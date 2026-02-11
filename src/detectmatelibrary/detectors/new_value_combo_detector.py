from detectmatelibrary.common._config import generate_detector_config
from detectmatelibrary.common._config._formats import EventsConfig

from detectmatelibrary.common.detector import CoreDetectorConfig, CoreDetector, get_configured_variables

from detectmatelibrary.utils.data_buffer import BufferMode
from detectmatelibrary.utils.persistency.event_data_structures.trackers import (
    EventStabilityTracker
)
from detectmatelibrary.utils.persistency.event_persistency import EventPersistency

from detectmatelibrary.schemas import ParserSchema, DetectorSchema

from typing import Any, Dict, Sequence, cast, Tuple
from itertools import combinations


def get_combo(variables: Dict[str, Any]) -> Dict[Tuple[str, ...], Tuple[Any, ...]]:
    """Get a single combination of all variables as a key-value pair."""
    return {tuple(variables.keys()): tuple(variables.values())}


def _combine(
    iterable: Sequence[str], max_combo_length: int = 2
) -> list[Tuple[str, ...]]:
    """Get all possible combinations of an iterable."""
    combos: list[Tuple[str, ...]] = []
    for i in range(2, min(len(iterable), max_combo_length, 5) + 1):
        combo = list(combinations(iterable, i))
        combos.extend(combo)
    return combos


def get_all_possible_combos(
    variables: Dict[str, Any], max_combo_length: int = 2
) -> Dict[Tuple[str, ...], Tuple[Any, ...]]:
    """Get all combinations of specified variables as key-value pairs."""
    combo_dict = {}
    combos = _combine(list(variables.keys()), max_combo_length)
    for combo in combos:
        key = tuple(combo)  # Use tuple of variable names as key
        value = tuple(variables[var] for var in combo)
        combo_dict[key] = value
    return combo_dict


class NewValueComboDetectorConfig(CoreDetectorConfig):
    method_type: str = "new_value_combo_detector"

    events: EventsConfig | dict[str, Any] = {}
    comb_size: int = 2


class NewValueComboDetector(CoreDetector):
    def __init__(
        self,
        name: str = "NewValueComboDetector",
        config: NewValueComboDetectorConfig = NewValueComboDetectorConfig()
    ) -> None:

        if isinstance(config, dict):
            config = NewValueComboDetectorConfig.from_dict(config, name)
        super().__init__(name=name, buffer_mode=BufferMode.NO_BUF, config=config)

        self.config = cast(NewValueComboDetectorConfig, self.config)
        self.persistency = EventPersistency(
            event_data_class=EventStabilityTracker,
            event_data_kwargs={"converter_function": get_combo}
        )
        # auto config checks if individual variables are stable to select combos from
        self.auto_conf_persistency = EventPersistency(
            event_data_class=EventStabilityTracker
        )
        self.auto_conf_persistency_combos = EventPersistency(
            event_data_class=EventStabilityTracker,
            event_data_kwargs={"converter_function": get_all_possible_combos}
        )

        # TEMPORARY:
        self.inputs: list[ParserSchema] = []

    def train(self, input_: ParserSchema) -> None:  # type: ignore
        config = cast(NewValueComboDetectorConfig, self.config)
        configured_variables = get_configured_variables(input_, config.events)
        self.persistency.ingest_event(
            event_id=input_["EventID"],
            event_template=input_["template"],
            named_variables=configured_variables
        )

    def detect(
        self, input_: ParserSchema, output_: DetectorSchema  # type: ignore
    ) -> bool:
        alerts: Dict[str, str] = {}
        config = cast(NewValueComboDetectorConfig, self.config)
        configured_variables = get_configured_variables(input_, config.events)
        combo_dict = get_combo(configured_variables)

        overall_score = 0.0
        for event_id, event_tracker in self.persistency.get_events_data().items():
            for combo_key, multi_tracker in event_tracker.get_data().items():
                # Get the value tuple for this combo key
                value_tuple = combo_dict.get(combo_key)
                if value_tuple is None:
                    continue
                if value_tuple not in multi_tracker.unique_set:
                    alerts[f"EventID {event_id}"] = (
                        f"Unknown value combination: {value_tuple}"
                    )
                    overall_score += 1.0

        if overall_score > 0:
            output_["score"] = overall_score
            output_["description"] = (
                f"{self.name} detects value combinations not encountered "
                "in training as anomalies."
            )
            output_["alertsObtain"].update(alerts)
            return True
        return False

    def configure(self, input_: ParserSchema) -> None:
        """Configure the detector based on the stability of individual
        variables, then learn value combinations based on that
        configuration."""
        # store inputs to re-ingest after the first step of the configuration process
        self.inputs.append(input_)

        # first pass to learn variable stability of all variables
        self.auto_conf_persistency.ingest_event(
            event_id=input_["EventID"],
            event_template=input_["template"],
            variables=input_["variables"],
            named_variables=input_["logFormatVariables"],
        )

    def set_configuration(self, max_combo_size: int = 3) -> None:
        """Set the detector configuration based on the stability of variable
        combinations.

        The process is as follows:
        1. Analyze the stability of individual variables to identify which are stable.
        2. Generate an initial config with combos of stable variables.
        3. Re-ingest all events to learn the stability of these combos (testing all possible combos right away
        would explode combinatorially).
        """
        # run WITH auto_conf_persistency
        variable_combos = {}
        for event_id, tracker in self.auto_conf_persistency.get_events_data().items():
            stable_vars = tracker.get_variables_by_classification("STABLE")  # type: ignore
            if len(stable_vars) > 1:
                variable_combos[event_id] = stable_vars
        config_dict = generate_detector_config(
            variable_selection=variable_combos,
            detector_name=self.name,
            method_type=self.config.method_type,
            comb_size=max_combo_size
        )
        # Update the config object from the dictionary instead of replacing it
        self.config = NewValueComboDetectorConfig.from_dict(config_dict, self.name)

        # Re-ingest all inputs to learn combos based on new configuration
        for input_ in self.inputs:
            configured_variables = get_configured_variables(input_, self.config.events)
            # print(f"All POSSIBLE COMBOS: EVENT {input_['EventID']}: {all_possible_combos}\n")
            self.auto_conf_persistency_combos.ingest_event(
                event_id=input_["EventID"],
                event_template=input_["template"],
                named_variables=configured_variables
            )

        # rerun to set final config WITH auto_conf_persistency_combos
        combo_selection = {}
        for event_id, tracker in self.auto_conf_persistency_combos.get_events_data().items():
            stable_combos = tracker.get_variables_by_classification("STABLE")  # type: ignore
            # Keep combos as tuples - each will become a separate config entry
            if len(stable_combos) >= 1:
                combo_selection[event_id] = stable_combos
        config_dict = generate_detector_config(
            variable_selection=combo_selection,
            detector_name=self.name,
            method_type=self.config.method_type,
            comb_size=max_combo_size
        )
        # Update the config object from the dictionary instead of replacing it
        self.config = NewValueComboDetectorConfig.from_dict(config_dict, self.name)


# if __name__ == "__main__":
#     # Example: Testing the NewValueComboDetector
#     # This demonstrates the configuration and training workflow

#     # Create sample parsed log events (simulating authentication logs)
#     sample_events = [
#         # Normal login patterns - user1 always logs in from office IP
#         {"EventID": 4624, "template": "User <*> logged in from <*>",
#          "variables": ["user1", "192.168.1.100"],
#          "logFormatVariables": {"username": "user1", "src_ip": "192.168.1.100"}},
#         {"EventID": 4624, "template": "User <*> logged in from <*>",
#          "variables": ["user1", "192.168.1.100"],
#          "logFormatVariables": {"username": "user1", "src_ip": "192.168.1.100"}},
#         {"EventID": 4624, "template": "User <*> logged in from <*>",
#          "variables": ["user1", "192.168.1.100"],
#          "logFormatVariables": {"username": "user1", "src_ip": "192.168.1.100"}},

#         # user2 always logs in from home IP
#         {"EventID": 4624, "template": "User <*> logged in from <*>",
#          "variables": ["user2", "10.0.0.50"],
#          "logFormatVariables": {"username": "user2", "src_ip": "10.0.0.50"}},
#         {"EventID": 4624, "template": "User <*> logged in from <*>",
#          "variables": ["user2", "10.0.0.50"],
#          "logFormatVariables": {"username": "user2", "src_ip": "10.0.0.50"}},
#         {"EventID": 4624, "template": "User <*> logged in from <*>",
#          "variables": ["user2", "10.0.0.50"],
#          "logFormatVariables": {"username": "user2", "src_ip": "10.0.0.50"}},

#         # Different event type - file access
#         {"EventID": 4663, "template": "User <*> accessed file <*>",
#          "variables": ["user1", "/data/report.pdf"],
#          "logFormatVariables": {"username": "user1", "filepath": "/data/report.pdf"}},
#         {"EventID": 4663, "template": "User <*> accessed file <*>",
#          "variables": ["user1", "/data/report.pdf"],
#          "logFormatVariables": {"username": "user1", "filepath": "/data/report.pdf"}},
#                  # Normal login patterns - user1 always logs in from office IP
#         {"EventID": 4624, "template": "User <*> logged in from <*>",
#          "variables": ["user1", "192.168.1.100"],
#          "logFormatVariables": {"username": "user1", "src_ip": "192.168.1.100"}},
#         {"EventID": 4624, "template": "User <*> logged in from <*>",
#          "variables": ["user1", "192.168.1.100"],
#          "logFormatVariables": {"username": "user1", "src_ip": "192.168.1.100"}},
#         {"EventID": 4624, "template": "User <*> logged in from <*>",
#          "variables": ["user1", "192.168.1.100"],
#          "logFormatVariables": {"username": "user1", "src_ip": "192.168.1.100"}},

#         # user2 always logs in from home IP
#         {"EventID": 4624, "template": "User <*> logged in from <*>",
#          "variables": ["user2", "10.0.0.50"],
#          "logFormatVariables": {"username": "user2", "src_ip": "10.0.0.50"}},
#         {"EventID": 4624, "template": "User <*> logged in from <*>",
#          "variables": ["user2", "10.0.0.50"],
#          "logFormatVariables": {"username": "user2", "src_ip": "10.0.0.50"}},
#         {"EventID": 4624, "template": "User <*> logged in from <*>",
#          "variables": ["user2", "10.0.0.50"],
#          "logFormatVariables": {"username": "user2", "src_ip": "10.0.0.50"}},

#         # Different event type - file access
#         {"EventID": 4663, "template": "User <*> accessed file <*>",
#          "variables": ["user1", "/data/report.pdf"],
#          "logFormatVariables": {"username": "user1", "filepath": "/data/report.pdf"}},
#         {"EventID": 4663, "template": "User <*> accessed file <*>",
#          "variables": ["user1", "/data/report.pdf"],
#          "logFormatVariables": {"username": "user1", "filepath": "/data/report.pdf"}},
#                  # Normal login patterns - user1 always logs in from office IP
#         {"EventID": 4624, "template": "User <*> logged in from <*>",
#          "variables": ["user1", "192.168.1.100"],
#          "logFormatVariables": {"username": "user1", "src_ip": "192.168.1.100"}},
#         {"EventID": 4624, "template": "User <*> logged in from <*>",
#          "variables": ["user1", "192.168.1.100"],
#          "logFormatVariables": {"username": "user1", "src_ip": "192.168.1.100"}},
#         {"EventID": 4624, "template": "User <*> logged in from <*>",
#          "variables": ["user1", "192.168.1.100"],
#          "logFormatVariables": {"username": "user1", "src_ip": "192.168.1.100"}},

#         # user2 always logs in from home IP
#         {"EventID": 4624, "template": "User <*> logged in from <*>",
#          "variables": ["user2", "10.0.0.50"],
#          "logFormatVariables": {"username": "user2", "src_ip": "10.0.0.50"}},
#         {"EventID": 4624, "template": "User <*> logged in from <*>",
#          "variables": ["user2", "10.0.0.50"],
#          "logFormatVariables": {"username": "user2", "src_ip": "10.0.0.50"}},
#         {"EventID": 4624, "template": "User <*> logged in from <*>",
#          "variables": ["user2", "10.0.0.50"],
#          "logFormatVariables": {"username": "user2", "src_ip": "10.0.0.50"}},

#         # Different event type - file access
#         {"EventID": 4663, "template": "User <*> accessed file <*>",
#          "variables": ["user1", "/data/report.pdf"],
#          "logFormatVariables": {"username": "user1", "filepath": "/data/report.pdf"}},
#         {"EventID": 4663, "template": "User <*> accessed file <*>",
#          "variables": ["user1", "/data/report.pdf"],
#          "logFormatVariables": {"username": "user1", "filepath": "/data/report.pdf"}},
#     ]

#     # Create ParserSchema objects from sample data
#     parser_schemas = [ParserSchema(kwargs=event) for event in sample_events]

#     # Initialize the detector
#     detector = NewValueComboDetector(name="TestComboDetector")

#     print("=" * 60)
#     print("NewValueComboDetector Example")
#     print("=" * 60)

#     # Phase 1: Configuration - learn which variables are stable
#     print("\n[Phase 1] Running configuration phase...")
#     for schema in parser_schemas:
#         detector.configure(schema)

#     # Set configuration based on learned stable variables
#     print("PERSISTENCY",detector.auto_conf_persistency.get_events_data())
#     detector.set_configuration(max_combo_size=2)

#     # Phase 2: Training - learn normal value combinations
#     print("\n[Phase 2] Running training phase...")
#     for schema in parser_schemas:
#         detector.train(schema)

#     # Show what the detector learned
#     print("\nLearned event data:")
#     print(detector.persistency.get_events_data())

#     # Phase 3: Detection (note: detect method is incomplete in current code)
#     print("\n[Phase 3] Detection phase...")

#     # Example anomalous event - user1 logging in from unusual IP
#     anomalous_event = {
#         "EventID": 4624,
#         "template": "User <*> logged in from <*>",
#         "variables": ["MALICIOUS_USER", "MALICIOUS_IP"],
#         "logFormatVariables": {"username": "MALICIOUS_USER", "src_ip": "MALICIOUS_IP"},
#     }
#     benign_event = {
#         "EventID": 4624,
#         "template": "User <*> logged in from <*>",
#         "variables": ["user1", "192.168.1.100"],
#         "logFormatVariables": {"username": "user1", "src_ip": "192.168.1.100"},
#     }
#     anomalous_schema = ParserSchema(kwargs=anomalous_event)
#     benign_schema = ParserSchema(kwargs=benign_event)

#     # Create output schema for detection results
#     output_schema = DetectorSchema(kwargs={"alertsObtain": {}})

#     anomalies = []
#     for schema in [anomalous_schema, benign_schema]:
#         anomalous = detector.detect(schema, output_=output_schema)
#         anomalies.append(anomalous)

#     print("\nDetection output:")
#     print(anomalies)

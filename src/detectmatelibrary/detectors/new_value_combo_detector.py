from detectmatelibrary.common._config._formats import LogVariables, AllLogVariables
from detectmatelibrary.common._config import generate_detector_config

from detectmatelibrary.common.detector import CoreDetectorConfig
from detectmatelibrary.common.detector import CoreDetector

from detectmatelibrary.utils.data_buffer import BufferMode

from detectmatelibrary.common.persistency.event_data_structures.trackers import (
    EventStabilityTracker
)
from detectmatelibrary.common.persistency.event_persistency import EventPersistency

import detectmatelibrary.schemas as schemas

from typing import Any, Set, Dict, cast, Tuple


def get_combo(variables: Dict[str, Any]) -> Dict[str, Tuple[Any, ...]]:
    """Get a single combination of all variables as a key-value pair."""
    return {"-".join(variables.keys()): tuple(variables.values())}


#  *********************************************************************
class NewValueComboDetectorConfig(CoreDetectorConfig):
    method_type: str = "new_value_combo_detector"

    log_variables: LogVariables | AllLogVariables | dict[str, Any] = {}
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
        self.known_combos: Dict[str | int, Set[Any]] = {"all": set()}
        self.persistency = EventPersistency(
            event_data_class=EventStabilityTracker,
            event_data_kwargs={"converter_function": get_combo}
        )
        # auto config checks if individual variables are stable to select combos from
        self.auto_conf_persistency = EventPersistency(
            event_data_class=EventStabilityTracker
        )

    def train(self, input_: schemas.ParserSchema) -> None:  # type: ignore
        self.persistency.ingest_event(
            event_id=input_["EventID"],
            event_template=input_["template"],
            variables=input_["variables"],
            log_format_variables=input_["logFormatVariables"],
        )

    def detect(
        self, input_: schemas.ParserSchema, output_: schemas.DetectorSchema  # type: ignore
    ) -> bool:
        alerts: Dict[str, str] = {}

        all_variables = self.persistency.get_all_variables(
            variables=input_["variables"],
            log_format_variables=input_["logFormatVariables"],
        )
        combo = tuple(get_combo(all_variables).items())[0]

        for event_id, event_tracker in self.persistency.get_events_data().items():
            for event_id, multi_tracker in event_tracker.get_data().items():
                if combo not in multi_tracker.unique_set:
                    alerts[f"EventID {event_id}"] = (
                        f"Unknown value combination: {combo}"
                    )
        if alerts:
            output_["alertsObtain"] = alerts
            return True
        return False

    def configure(self, input_: schemas.ParserSchema) -> None:
        self.auto_conf_persistency.ingest_event(
            event_id=input_["EventID"],
            event_template=input_["template"],
            variables=input_["variables"],
            log_format_variables=input_["logFormatVariables"],
        )

    def set_configuration(self, max_combo_size: int = 6) -> None:
        variable_combos = {}
        templates = {}
        for event_id, tracker in self.auto_conf_persistency.get_events_data().items():
            stable_vars = tracker.get_variables_by_classification("STABLE")  # type: ignore
            if len(stable_vars) > 1:
                variable_combos[event_id] = stable_vars
                templates[event_id] = self.auto_conf_persistency.get_event_template(event_id)
        config_dict = generate_detector_config(
            variable_selection=variable_combos,
            templates=templates,
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
#     parser_schemas = [schemas.ParserSchema(kwargs=event) for event in sample_events]

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
#     detector.set_configuration(max_combo_size=2)

#     print(f"Configured log_variables: {detector.config.log_variables}")
#     print(f"Combo size: {detector.config.comb_size}")

#     # Phase 2: Training - learn normal value combinations
#     print("\n[Phase 2] Running training phase...")
#     for schema in parser_schemas:
#         detector.train(schema)

#     # Show what the detector learned
#     print("\nLearned event data:")
#     for event_id, tracker in detector.persistency.get_events_data().items():
#         print(f"  EventID {event_id}: {tracker}")

#     # Phase 3: Detection (note: detect method is incomplete in current code)
#     print("\n[Phase 3] Detection phase...")
#     print("Note: The detect() method is currently incomplete.")

#     # Example anomalous event - user1 logging in from unusual IP
#     anomalous_event = {
#         "EventID": 4624,
#         "template": "User <*> logged in from <*>",
#         "variables": ["MALICIOUS_USER", "MALICIOUS_IP"],
#         "logFormatVariables": {"username": "MALICIOUS_USER", "src_ip": "MALICIOUS_IP"},
#     }
#     anomalous_schema = schemas.ParserSchema(kwargs=anomalous_event)


#     # Create output schema for detection results
#     output_schema = schemas.DetectorSchema(kwargs={"alertsObtain": {}})

#     for schema in [anomalous_schema]:
#         detector.detect(schema, output_=output_schema)

#     print("\nDetection output:")
#     print(output_schema)

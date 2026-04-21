import detectmatelibrary.detectors.rule_detector as rd
import detectmatelibrary.schemas as schemas

import pytest


class TestCaseRules:
    def test_template_not_found(self) -> None:
        parsed_log = schemas.ParserSchema({"EventID": -1})

        alert, msg = rd.template_not_found(parsed_log)
        assert alert
        assert "Template was not found by the parser" == msg

        parsed_log = schemas.ParserSchema({"EventID": 2})
        alert, _ = rd.template_not_found(parsed_log)
        assert not alert

    def test_find_keyword(self) -> None:
        keywords = ["hello", "ciao"]

        parsed_log = schemas.ParserSchema({"log": "hello world"})
        alert, msg = rd.find_keyword(parsed_log, keywords)
        assert alert
        assert "Found word 'hello' in the logs" == msg

        parsed_log = schemas.ParserSchema({"log": "ciao world"})
        alert, msg = rd.find_keyword(parsed_log, keywords)
        assert alert
        assert "Found word 'ciao' in the logs" == msg

        parsed_log = schemas.ParserSchema({"log": "world"})
        alert, _ = rd.find_keyword(parsed_log, keywords)
        assert not alert

    def test_find_exceptions(self) -> None:
        parsed_log = schemas.ParserSchema({"log": "hello Exception"})
        alert, msg = rd.exceptions(parsed_log)
        assert alert
        assert "Found word 'exception' in the logs" == msg

        parsed_log = schemas.ParserSchema({"log": "world"})
        alert, _ = rd.exceptions(parsed_log)
        assert not alert

    def test_error_log(self) -> None:
        parsed_log = schemas.ParserSchema(
            {"logFormatVariables": {"Level": "Error"}}
        )
        alert, msg = rd.error_log(parsed_log)
        assert alert
        assert "Error found" == msg

        parsed_log = schemas.ParserSchema(
            {"logFormatVariables": {"Level": "Info"}}
        )
        alert, _ = rd.error_log(parsed_log)
        assert not alert

        parsed_log = schemas.ParserSchema({"log": "hello world"})
        alert, _ = rd.error_log(parsed_log)
        assert not alert


class TestCaseRuleDetector:
    def test_run_all_rules(self) -> None:
        rule_detector = rd.RuleDetector()

        assert rule_detector.process(schemas.ParserSchema()) is None

        alert1 = rule_detector.process(schemas.ParserSchema(
            {
                "EventID": -1,
                "log": "fail exception",
                "logFormatVariables": {"Level": "Error"}
            }
        ))
        assert alert1 is not None
        assert alert1["alertsObtain"] == {
            "R001 - TemplateNotFound": "Template was not found by the parser",
            "R003 - CheckForExceptions": "Found word 'exception' in the logs",
            "R004 - ErrorLevelFound": "Error found",
        }
        assert alert1["score"] == 3

    def test_all_rules_serialize(self) -> None:
        rule_detector = rd.RuleDetector()

        assert rule_detector.process(schemas.ParserSchema().serialize()) is None

        alert1 = rule_detector.process(schemas.ParserSchema(
            {
                "EventID": -1,
                "log": "fail exception",
                "logFormatVariables": {"Level": "Error"}
            }
        ).serialize())
        assert alert1 is not None

        (alert := schemas.DetectorSchema()).deserialize(alert1)
        assert alert["alertsObtain"] == {
            "R001 - TemplateNotFound": "Template was not found by the parser",
            "R003 - CheckForExceptions": "Found word 'exception' in the logs",
            "R004 - ErrorLevelFound": "Error found",
        }
        assert alert["score"] == 3

    def test_run_single_rule(self) -> None:
        rule_detector = rd.RuleDetector(
            name="RuleDetector",
            config={
                "detectors": {
                    "RuleDetector": {
                        "method_type": "rule_detector",
                        "auto_config": False,
                        "params": {
                            "rules": [
                                {"rule": "R001 - TemplateNotFound"}
                            ]
                        }
                    }
                }
            }
        )

        assert rule_detector.process(schemas.ParserSchema()) is None

        alert1 = rule_detector.process(schemas.ParserSchema(
            {
                "EventID": -1,
                "log": "fail exception",
                "logFormatVariables": {"Level": "Error"}
            }
        ))
        assert alert1 is not None
        assert alert1["alertsObtain"] == {
            "R001 - TemplateNotFound": "Template was not found by the parser",
        }
        assert alert1["score"] == 1

    def test_run_single_rule_with_args(self) -> None:
        rule_detector = rd.RuleDetector(
            name="RuleDetector",
            config={
                "detectors": {
                    "RuleDetector": {
                        "method_type": "rule_detector",
                        "auto_config": False,
                        "params": {
                            "rules": [
                                {"rule": "R002 - SpecificKeyword", "args": ["hi", "kenobi"]}
                            ]
                        }
                    }
                }
            }
        )

        assert rule_detector.process(schemas.ParserSchema({"log": "ciao"})) is None
        assert rule_detector.process(schemas.ParserSchema({"log": "hi"})) is not None

    def test_rule_not_found(self) -> None:

        with pytest.raises(rd.RuleNotFound):
            rd.RuleDetector(
                name="RuleDetector",
                config={
                    "detectors": {
                        "RuleDetector": {
                            "method_type": "rule_detector",
                            "auto_config": False,
                            "params": {
                                "rules": [
                                    {"rule": "Rule made up"}
                                ]
                            }
                        }
                    }
                }
            )

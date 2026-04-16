import detectmatelibrary.detectors.rule_detector as rd
import detectmatelibrary.schemas as schemas


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

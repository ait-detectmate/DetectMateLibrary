"""Tests for detectmatelibrary.parsers.template_matcher._matcher_op."""
from detectmatelibrary.parsers.template_matcher._matcher_op import Preprocess


class TestPreprocessingMatcher:
    def test_convert_lower_cases(self):
        preprocess = Preprocess(re_punctuation=False, re_spaces=False, do_lowercase=True)
        assert preprocess("Hello! hOw  is going") == "hello! how  is going"

    def test_remove_punctuation(self):
        preprocess = Preprocess(re_punctuation=True, re_spaces=False, do_lowercase=False)
        assert preprocess("Hello! hOw  is going") == "Hello hOw  is going"

    def test_remove_spaces(self):
        preprocess = Preprocess(re_punctuation=False, re_spaces=True, do_lowercase=False)
        assert preprocess("Hello! hOw  is going") == "Hello! hOw is going"

    def test_all_cases(self):
        preprocess = Preprocess(re_punctuation=True, re_spaces=True, do_lowercase=True)
        assert preprocess("Hello! hOw  is going") == "hello how is going"

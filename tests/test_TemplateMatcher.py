import pandas as pd

from detectmatelibrary.parsers.template_matcher import TemplateMatcher


log_df = pd.read_csv("tests/test_folder/logs_with_template_labels.csv")
test_template = "pid=<*> uid=<*> auid=<*> ses=<*> msg='op=PAM:<*> acct=<*> exe=<*> " \
                "hostname=<*> addr=<*> terminal=<*> res=<*>"
test_log = 'pid=9699 uid=0 auid=4294967295 ses=4294967295 msg=\'op=PAM:accounting ' \
           'acct="root" exe="/usr/sbin/cron" hostname=? addr=? terminal=cron res=success\''


class TestParsing():
    def test_TemplateMatcher_matched(self):
        logs_df = pd.DataFrame([test_log], columns=['Content'])
        template_matcher = TemplateMatcher([test_template])
        assert template_matcher.match_logs(logs_df)["EventTemplate"][0] == test_template

    def test_TemplateMatcher_unmatched(self):
        log = 'this is not matching'
        logs_df = pd.DataFrame([log], columns=['Content'])
        template_matcher = TemplateMatcher([test_template])
        assert not template_matcher.match_logs(logs_df)["EventTemplate"][0] == test_template

    def test_Apache_logs(self):
        templates = log_df["EventTemplate"].unique().tolist()
        template_matcher = TemplateMatcher(templates)
        matched_logs_df = template_matcher.match_logs(log_df.drop(columns=["EventTemplate"]))
        assert matched_logs_df["EventTemplate"].notnull().all()

# AGENTS.md (tests/)

Checklist to apply every time, without exception. For the *why* behind any
rule here, see `tests/README.md`.

## Non-negotiable rules

- `unit/<dir>/test_<module>[_<topic>].py` must mirror
  `src/detectmatelibrary/<dir>/<module>.py` one-to-one; `test_layout.py`
  enforces this and fails the build if it's broken.
- Every test module starts with a one-line docstring saying what it covers.
- A new parser/detector/aggregator/tracker gets a case in
  `tests/contract/registry.py` — a unit test file alone is not enough; the
  contract suites are what check construction, YAML round trip, outputs,
  alerts, persistence and federation.
- Never write into `tests/test_data/`. Test outputs go to the test's own
  temporary working directory.
- Never hand-edit a golden file. Regenerate with
  `uv run pytest tests/e2e -m "" --update-golden`, then review
  `git diff tests/test_data/golden/` like code before committing it. Never
  run `--update-golden` just to make a failing test pass — if you didn't
  intend every change in that diff, you have a bug, not a stale golden file.
- DeepLog/LogBERT are judged against bounds
  (`<Detector>.thresholds.json`: a minimum share of labelled anomalies found,
  a maximum number of false alarms), never an exact alert set. Don't write
  or request an assertion that expects exact output from either.
- A known bug is pinned by `xfail(strict=True)` asserting the **correct**
  behaviour, not the buggy one (see the bug table in `tests/README.md`).
  Don't "fix" such a test to match the bug. When the bug is actually fixed,
  remove the marker and update any golden files the fix changes.
- Databases: use the `mongo_db` / `redis_dbs` fixtures, never a hardcoded
  database name.
- Time: use the `frozen_timestamps` fixture for byte-for-byte output
  comparisons; never `time.sleep()` to wait on a thread — use
  `tests/support/timing.py::wait_until`.
- Level markers (`unit`/`contract`/`integration`/`e2e`) come from the
  directory alone — never add one by hand.

## Before claiming the suite is green

- `uv run pytest` is the default run (skips `slow`, `cli`, `docs`).
  `uv run pytest -m ""` is what CI runs — use this, not the default run,
  before reporting the suite as passing.
- Coverage gate (combined statement+branch percentage):
  `uv run pytest -m "" --cov=detectmatelibrary --cov-branch --cov-fail-under=79`
  (mirrors `.github/workflows/python-app.yml`).

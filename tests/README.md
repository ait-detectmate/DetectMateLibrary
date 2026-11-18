# Tests

How the DetectMateLibrary test suite is organised, how to run it, and where a new test goes.

## Running the tests

```bash
uv run pytest                        # default run: everything except slow, cli and docs tests (about 1 min)
uv run pytest -m ""                  # everything, as CI runs it (about 9 min)
uv run pytest tests/unit             # one level: unit, contract, integration or e2e
uv run pytest -m slow                # only the opt-in slow tests
uv run pytest tests/unit/detectors/test_new_value_detector.py   # one file
uv run pytest -m "" --cov=detectmatelibrary --cov-branch --cov-report=term-missing
```

Which tests ran a given line: run with `--cov=detectmatelibrary --cov-context=test`, then `uv run coverage html --show-contexts` and open `htmlcov/index.html`.

Tests that need MongoDB or Redis are skipped locally when the server doesn't answer. Start both with

```bash
docker compose -f tests/compose.yaml up -d
```

Or point the tests at other servers with `MONGO_URL` (default `mongodb://localhost:27017`) and `REDIS_URL` (default `redis://localhost:6379`).

## Layout

```
tests/
├── unit/          one source module per test file, mirroring src/detectmatelibrary/
├── contract/      one interface, checked for every implementation (registry.py)
├── integration/   several real components, or a real database
├── e2e/           raw logs to alerts through public entry points only
├── support/       shared helpers (paths, golden files, timing, databases, synthetic data)
├── test_data/     input files, golden files (golden/), the synthetic session log (sessions/)
├── conftest.py    level markers, opt-in groups, required services, isolation fixtures
└── test_layout.py guards the rules below
```

| Level | A test belongs here when it … | Example |
|---|---|---|
| `unit/` | tests one module, with real collaborators only where they are cheap | `unit/utils/test_key_extractor.py` |
| `contract/` | states a promise every parser / detector / aggregator / tracker must keep | `contract/test_detector_contract.py` |
| `integration/` | wires several components or a real service together, without being a full chain | `integration/test_mongo_connector.py` |
| `e2e/` | starts from raw log text or files and ends at alerts, aggregates, stored records or output files, using only `process()`, `Pipeline`, `From`/`To`, `XSchema.from_id` or the CLI | `e2e/test_detector_regression.py` |

`test_layout.py` checks:
- that `tests/` holds only these entries, and that every test directory is a package;
- that `unit/` mirrors `src/`: `unit/<dir>/test_<module>[_<topic>].py` tests `src/detectmatelibrary/<dir>/<module>.py`, and `test_<package>.py` tests a package's `__init__.py`;
- that every source module has a unit test file, or an entry with a reason in `NO_UNIT_TEST_FILE`;
- that every test module starts with a docstring saying what it covers.

### e2e chains

| Chain | File | What it checks |
|---|---|---|
| C1 | `test_component_chain.py` | parser → detector → aggregator as separate components; bytes at every hop equal the object run |
| C2 | `test_pipeline.py` | `Pipeline` with and without parsing / aggregation, 1 or 3 workers, two log sources |
| C3 | `test_detector_regression.py`, `test_sessions.py` | every detector driven only by `process()` and its config, against golden files; DeepLog/LogBERT against recall and false-alarm bounds; session windows on interleaved sessions |
| C4 | `test_restart.py` | a trained detector saved and restored (`export_state`/`import_state`, `persist:` + `auto_load`) |
| C5 | `test_federation.py` | three trained clients aggregated into an untrained server |
| C6 | `test_file_io.py` | `FromTo` file chain: log → JSON → detector → YAML |
| C7 | `test_config_driven.py` | a `Pipeline` from a YAML file; named templates and variables |
| C8 | `test_json_chain.py` | JSON log lines through `JsonParser` |
| C9 | `test_connectors.py` | every stage reads back what it stored (Verification, MongoDB, Redis) |
| — | `test_doc_examples.py`, `test_workspace_cli.py` | every `docs/examples/**/*.py` runs; `mate create` and the generated tests |

## Markers

Level markers (`unit`, `contract`, `integration`, `e2e`) come from the directory; nobody writes them by hand. The others say *why* a test is not in the default run:

| Marker | Meaning | Local default run | CI |
|---|---|---|---|
| `slow` | takes more than about 2 s | left out | runs |
| `cli` | runs the installed `mate` console script | left out | runs |
| `docs` | runs a file from `docs/examples/` | left out | runs |
| `needs_cxx` | needs a C++ compiler (torch.compile) | skipped if there is none | fails if there is none |
| `needs_mongo`, `needs_redis` | need a database server | skipped if unreachable | fail if unreachable |

## Writing a test

- **A new component** gets a case in `tests/contract/registry.py`. The contract suites then check its construction, YAML round trip, outputs, alerts, persistence and federation. Its unit test file only needs what is specific to it.
- **Global state is isolated automatically** (`conftest.py`): every test runs in its own temporary working directory. The schema connector, the time test mode, NumPy's global RNG, the root logger and the `memory://` filesystem are restored after each test. A leaked `PersistencySaver` timer fails the test.
- **Shared default configs (bug B1):** a guard in `conftest.py` restores any component default config a test changed, and lists those tests at the end of the run. A test that relies on a fresh default must not depend on that guard; build components with their own config.
- **Time:** `get_timestamp()` reads the real clock; use the `frozen_timestamps` fixture where outputs are compared byte for byte. Never `time.sleep()` to wait for a thread: use `tests/support/timing.py::wait_until`.
- **Databases:** take the database from the `mongo_db` / `redis_dbs` fixtures, never a fixed name. Mongo gets a fresh database per test; Redis uses databases 10–12, flushed before and after (`REDIS_TEST_DB` moves the range).
- **Files:** read inputs through `tests/support/paths.py`; write outputs to relative paths (the test's own directory). Never write into `tests/test_data/`.

## Golden files

`tests/test_data/golden/` holds what the e2e chains produced on fixed input, with the settings that produced them: `audit/` (one per detector, C3), `pipeline/` (C2), `sessions/`. A test compares a fresh run with its golden file.

When a change to the library changes the output on purpose:

```bash
uv run pytest tests/e2e -m "" --update-golden    # rewrites the golden files; refused when CI is set
git diff tests/test_data/golden/                  # review the change like code
```

DeepLog and LogBERT are not compared exactly. Their `<Detector>.thresholds.json` holds a minimum number of labelled anomalies to find and a maximum number of false alarms, both measured from one seeded run; `--update-golden` measures them again.

The session log `tests/test_data/sessions/sessions.log` is generated: `uv run python -m tests.support.sessions` rewrites it, and `e2e/test_sessions.py` checks that file and generator agree.

## Known bugs and open questions

A known bug is pinned by a test marked `xfail(strict=True)` that asserts the **correct** behaviour. When the bug is fixed the test passes, strict mode turns that into a failure, and the marker must go (together with any golden files the fix changes).

| ID | Bug | Pinned by |
|---|---|---|
| B1 | components share one default config instance, and some change it | `contract/test_component_contract.py::test_default_config_is_not_shared`, `contract/test_auto_config_contract.py::test_configuring_one_detector_leaves_new_ones_unconfigured` |
| B2 | `Pipeline.output_schema` is inverted | `unit/test_pipeline.py::test_output_schema_matches_aggregation` |
| B3 | `selectComponent` can't find DeepLog / LogBERT | `contract/test_component_contract.py::test_select_component_finds_the_class` |
| B4 | ECVC reseeds NumPy's global RNG | `unit/detectors/test_ecvc_detector.py::test_training_leaves_the_global_numpy_rng_alone` |
| B6 | TreeMatcher keeps a partial match's variables | `contract/test_parser_contract.py::test_a_log_that_matches_no_template_has_no_event` |
| B7 | `finalize_federation()` deletes every detector's table | `unit/base_detectors/test_tracker_detector.py::TestFinalizeFederation::test_leaves_other_detectors_tables_alone` |
| B8 | importing LogBatcher breaks `selectComponent` for parsers | `unit/helper/test_select_component.py::test_finds_a_parser_after_logbatcher_was_imported` |
| B9 | NewEvent with a global instance alerts on every log | `integration/test_global_instances.py::test_global_instance_flags_the_expected_logs[NewEventDetector]` |
| B10 | without a training phase `post_train()` never runs | `unit/common/test_core.py::TestPostTrain::test_post_train_follows_the_replayed_configure_records` |
| B11 | persistency equality ignores what the trackers learned | `unit/utils/persistency/test_basic_persistency.py::TestPersistencyStructEquality::test_different_learned_values_are_not_equal` |

Open questions (no test pins either answer yet):

| ID | Question |
|---|---|
| Q-A | Should DeepLog / LogBERT keep the fine-tuning result in their config? |
| Q-B | Should `selectComponent` keep the instance name? (`B5` is reserved for it if the answer is yes) |
| Q-C | Should a connector hide a database outage (today it only warns)? |
| Q-D | Should `JsonParser` keep the header variables of `log_format`? |
| Q-E | Is `BigramFrequencyDetector` meant to stay out of federation? |
| Q-F | Should a restored detector train again on its first records? |
| Q-H | `To.json` / `To.yaml` rewrite the whole file for every record |
| Q-I | Should a component reject the bytes of another schema? |

## CI

`.github/workflows/python-app.yml` runs the pre-commit hooks, starts MongoDB and Redis, and runs `uv run pytest -m ""` with coverage and a minimum (`--cov-fail-under`). The DetectMateService integration step at the end of that workflow belongs to the other repository and is still commented out.

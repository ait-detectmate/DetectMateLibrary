# Tutorial (end-to-end)

A complete walkthrough of using DetectMate  --  more detailed than the
[Quickstart](quickstart.md). The Quickstart parses a ready-made dataset with a
ready-made template file and runs one detector. This tutorial goes one level
deeper:

- you parse a dataset that has no template file yet, so you write the templates
  yourself
- you run two detectors that look for different kinds of anomalies and compare
  what each one finds
- you combine their alerts with an alert aggregator

By the end you should have seen most of what the library can do and, more
importantly, understand *why* each piece behaves the way it does.

## 1. Read a different dataset from scratch

The Quickstart uses the `audit.log` dataset, which already ships with a
matching `audit_templates.txt`. To actually practice building
something, this tutorial uses a different file instead:
`tests/test_data/logs.log`. It is still Linux `auditd` output  --  same overall
shape as the Quickstart's dataset  --  but recorded on a different machine, and
it comes with **no template file**. That is the point: before you can parse
it, you have to look at it.

> Note: you likely have to edit your Path to your project root. In this code snippet we assume, that your
> notebook lives two folders below the project root. If it sits somewhere else, adjust `parents[...]` (for a
> script) or the `Path.cwd()` line (for a notebook) accordingly.

```python
--8<-- "docs/examples/others/tutorial.py:read"
```

`From.log` is the same helper used in the Quickstart (see the
[From helper](../helper/from.md) docs). Passing `do_process=False`
turns it into a plain file reader that hands back [`LogSchema`](../schemas.md)
objects instead of running them through a parser  --  exactly what you want
before you've decided how to parse the data.

The file only has 9 lines, small enough to read in full:

```text
type=DAEMON_START msg=audit(1757673850.240:4506): op=start ver=3.0.9 format=enriched kernel=6.6.62+rpt-rpi-2712 auid=4294967295 pid=691 uid=0 ses=4294967295 res=success...
type=CONFIG_CHANGE msg=audit(1757673850.283:3): op=set audit_backlog_limit=8192 old=64 auid=4294967295 ses=4294967295 res=1...
type=SYSCALL msg=audit(1757673850.283:3): arch=c00000b7 syscall=206 success=yes exit=60 a0=3 a1=7fffc27ad8f0 a2=3c a3=0 items=0 ppid=696 pid=710 auid=4294967295 uid=0 gid=0 euid=0 suid=0 fsuid=0 egid=0 sgid=0 fsgid=0 tty=(none) ses=4294967295 comm="auditctl" exe="/usr/sbin/auditctl" key=(null)...
type=PROCTITLE msg=audit(1757673850.283:3): proctitle=2F7362696E2F617564697463746C002D52002F6574632F61756469742F61756469742E72756C6573
type=CONFIG_CHANGE msg=audit(1757673850.283:4): op=set audit_failure=1 old=1 auid=4294967295 ses=4294967295 res=1...
type=SYSCALL msg=audit(1757673850.283:4): arch=c00000b7 syscall=206 success=yes exit=60 a0=3 a1=7fffc27ad8f0 a2=3c a3=0 items=0 ppid=696 pid=710 auid=4294967295 uid=0 gid=0 euid=0 suid=0 fsuid=0 egid=0 sgid=0 fsgid=0 tty=(none) ses=4294967295 comm="auditctl" exe="/usr/sbin/auditctl" key=(null)...
type=PROCTITLE msg=audit(1757673850.283:4): proctitle=2F7362696E2F617564697463746C002D52002F6574632F61756469742F61756469742E72756C6573
type=CONFIG_CHANGE msg=audit(1757673850.283:5): op=set audit_backlog_wait_time=60000 old=15000 auid=4294967295 ses=4294967295 res=1...
type=SYSCALL msg=audit(1757673850.283:5): arch=c00000b7 syscall=206 success=yes exit=60 a0=3 a1=7fffc27ad8f0 a2=3c a3=0 items=0 ppid=696 pid=710 auid=4294967295 uid=0 gid=0 euid=0 suid=0 fsuid=0 egid=0 sgid=0 fsgid=0 tty=(none) ses=4294967295 comm="auditctl" exe="/usr/sbin/auditctl" key=(null)...
```

Every line starts with the same prefix shape, `type=<Type> msg=audit(<Time>:<Serial>):
<Content>`, and there are only four distinct *event types*  --  `DAEMON_START`,
`CONFIG_CHANGE`, `SYSCALL`, and `PROCTITLE`  --  each with its own static
template hiding behind the variable parts.

## 2. Build and configure your own parser

We reuse `MatcherParser` (the same parser class as the Quickstart, see
[Template Matcher](../parsers/template_matcher.md)), but this time we supply
our own `log_format` and write our own template file instead of a ready-made
one.

**Splitting off the prefix.** The `log_format` string tells the parser how to
carve off the `type=`/`msg=audit(...)` prefix into
`logFormatVariables` and hand the parser only the `<Content>` part to match
against templates:

```text
type=<Type> msg=audit(<Time>:<Serial>): <Content>
```

**Writing the templates.** **MatcherParser** needs a template file as an input. For each of the four content shapes above, we
replace the parts that change between log lines with `<*>`, following the
[template format](../parsers/template_matcher.md#template-format) rules  --  save the results in
`tests/test_data/logs_templates.txt`:

```text
op=start ver=<*> format=<*> kernel=<*> auid=<*> pid=<*> uid=<*> ses=<*> res=<*>
op=set <*> old=<*> auid=<*> ses=<*> res=<*>
arch=<*> syscall=<*> success=<*> exit=<*> a0=<*> a1=<*> a2=<*> a3=<*> items=<*> ppid=<*> pid=<*> auid=<*> uid=<*> gid=<*> euid=<*> suid=<*> fsuid=<*> egid=<*> sgid=<*> fsgid=<*> tty=<*> ses=<*> comm=<*> exe=<*> key=<*>
proctitle=<*>
```

A few things worth noticing while writing templates like these:

- The line number is the `EventID`  --  line 1 (0-indexed: `0`) matches
  `DAEMON_START`, line 2 (`1`) matches `CONFIG_CHANGE`, and so on, exactly as
  described in [EventID assignment](../parsers/template_matcher.md#eventid-assignment-preliminary).
- The second template's `op=set <*> old=<*> ...` has only one wildcard where
  the raw text has an `audit_backlog_limit=8192`, `audit_failure=1`, or
  `audit_backlog_wait_time=60000` key/value pair. A single `<*>` is not
  limited to one word  --  it happily captures the whole `key=value` chunk, so
  there's no need for a wildcard per key name even though the key itself
  varies between log lines.
- None of the templates need to account for the trailing `AUID="unset"
  UID="root"` fragment glued onto the end of each line (visible as `...` in
  the excerpt above). Because every template's last field is a `<*>`, that
  wildcard simply absorbs whatever comes after it.

**Configuring the parser:**

```python
--8<-- "docs/examples/others/tutorial.py:own_parser"
```

> **Common pitfall: don't escape `log_format` yourself.** The Quickstart's
> `log_format` string escapes the parentheses by hand:
> `r"...audit\(<Time>:<Serial>\):..."`. Don't copy that  --  it's wrong.
> `generate_logformat_regex()` (used internally by every parser that accepts
> `log_format`) already escapes every literal character outside the
> `<Placeholder>` tokens, parentheses included. Escaping them yourself asks it
> to match a **literal backslash** followed by `(`, which never occurs in
> real log data  --  the regex then silently fails to match anything, and every
> log falls back to `<Not Found>`. Write `log_format` as plain text; only the
> `<Placeholder>` tokens are special.

Running this prints, for each of the 9 logs, the `EventID` and the matched
template  --  all four templates get used, and every line matches (nothing
comes back as `<Not Found>`).

## 3. Run several detectors and compare their alerts

Different detectors look for different *kinds* of anomalies. To make that
concrete, this tutorial runs two of them side by side on the same parsed
stream:

- [**NewValueDetector**](../detectors/new_value.md) watches the *content* of
  specific fields and alerts when a value it hasn't been trained on shows up.
- [**EventSequenceDetector**](../detectors/event_sequence.md) ignores field
  content entirely and instead watches the *order* of `EventID`s, alerting
  when a sequence of consecutive events wasn't part of what it was trained
  on.

```python
--8<-- "docs/examples/others/tutorial.py:detectors"
```

Both detectors are configured with `data_use_training: 3`: the first 3 logs
(`DAEMON_START`, `CONFIG_CHANGE`, `SYSCALL`) are used to train, and detection
runs on the remaining 6  --  see [Configuration](../detectors.md#configuration)
for how `data_use_training` and `events` interact. `NewValueDetector` is
pointed at the two fields we identified while writing the templates in step
2: the `key=value` pair inside `CONFIG_CHANGE` (`EventID: 1`, `pos: 0`) and
the process name inside `SYSCALL` (`EventID: 2`, `pos: 22`, the `comm=` slot
counting `<*>` positions left to right in the third template line).

Running the loop prints one row per log line:

```text
 #  EventID  NewValue  EventSequence
 1        0     False          False
 2        1     False          False
 3        2     False          False
 4        3     False           True
 5        1      True           True
 6        2     False          False
 7        3     False           True
 8        1      True           True
 9        2     False          False
```

In the table above, **`True` means that detector raised an alert** for that log
(it found something anomalous), and **`False` means no alert**. With that in mind:
Reading the table alongside the raw data explains why each detector fires
when it does:

- **`NewValueDetector`** only fires on logs `#5` and `#8`  --  the second and
  third `CONFIG_CHANGE` events, whose `audit_failure=1` and
  `audit_backlog_wait_time=60000` values were never seen during training
  (only `audit_backlog_limit=8192`, from log `#2`, was). It stays silent on
  every `SYSCALL` after log `#3`, because `comm="auditctl"` is identical
  every time  --  there is nothing *new* about it once it's been trained once.
- **`EventSequenceDetector`** fires starting at log `#4`, and on every log
  after that except the `SYSCALL`s. With `fixed_window_size: 2`, training on
  the first 3 logs only teaches it the transitions `(DAEMON_START →
  CONFIG_CHANGE)` and `(CONFIG_CHANGE → SYSCALL)`. The transition `(SYSCALL →
  PROCTITLE)` at log `#4` was never trained, so it alerts  --  and keeps
  alerting every time that same transition recurs (`#7`), because alerts
  don't teach the detector anything; only `train()` does. `(PROCTITLE →
  CONFIG_CHANGE)` at log `#5` is equally untrained and alerts too, while
  `(CONFIG_CHANGE → SYSCALL)` at logs `#6` and `#9` was trained at log `#3`
  and stays quiet.

Note that both detectors agree on logs `#5` and `#8`  --  the same underlying
event looks anomalous from two independent angles: an unfamiliar value *and*
an unfamiliar position in the sequence. That overlap is what an alert
aggregator is for.

## 4. Add an alert aggregator

[Alert aggregation](../alert_aggregator.md) takes the stream of alerts coming
out of one or more detectors and combines them into
[`AggregateSchema`](../schemas.md) records. Here we feed every alert produced
in step 3  --  from either detector, in the order they were emitted  --  into
[`BasicConcatAggregation`](../alert_aggregators/basic_concatenation.md), the
simplest aggregation strategy available:

```python
--8<-- "docs/examples/others/tutorial.py:aggregate"
```

```text
['EventSequenceDetector', 'NewValueDetector'] ['3', '4']
['NewValueDetector', 'EventSequenceDetector'] ['4', '4']
['EventSequenceDetector', 'EventSequenceDetector'] ['4', '6']
['EventSequenceDetector', 'NewValueDetector'] ['6', '7']
['NewValueDetector', 'EventSequenceDetector'] ['7', '7']
```

Two details are easy to miss here, and both matter for production configs:

- **The buffer is a sliding window, not a batch.** `buffer_size: 2` does not
  mean "group alerts two at a time and clear." Alert aggregators use a
  [`WINDOW` buffer](../auxiliar/input_buffer.md) internally, so once 2 alerts
  have arrived, `aggregate_alerts()` fires again on *every* new alert,
  each time over the 2 most recently seen ones. Six alerts in therefore
  produce five overlapping aggregate outputs, not three separate batches.
- **`BasicConcatAggregation` does not correlate by log line.** It concatenates
  whatever alerts happen to be in the window, regardless of which log they
  refer to  --  that's why most rows above pair up alerts from *different*
  underlying logs. The two rows where both `logIDs` are identical
  (`['4', '4']` and `['7', '7']`) are the exception, and not a coincidence:
  those are exactly the log `#5` and `#8` cases from step 3, where
  `NewValueDetector` and `EventSequenceDetector` both alerted on the same
  event back to back, so the window happened to contain only that pair. A
  real deployment that wants alerts grouped *by log* rather than by arrival
  order needs a smarter aggregation strategy than basic concatenation.

## Common pitfalls

* Manually escaping regex characters (like `(` and `)`) inside a
  `log_format` string breaks matching
  `generate_logformat_regex()` already escapes literal text for you.
* A detector's `detect()` only checks `EventID`s it has already seen through
  `train()` at least once. If you configure a detector for an `EventID` that
  never appears in the training window (`data_use_training`), it will stay
  silent for that event type  --  not alert on everything, and not error either.
* Calling `.process()` on a detector or aggregator returns `None` when
  nothing fires, and the actual output schema (truthy) when it does  --  check
  with `if result:` rather than assuming a boolean.

Go back [Index](../index.md)

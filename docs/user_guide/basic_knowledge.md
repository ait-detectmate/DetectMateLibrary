# Basic knowledge

This page introduces the basic concepts you need before using DetectMate for log anomaly detection.

## What is a log?

Logs are messages produced by logging statements in code that describe events or
states during execution. For example:

```python
import logging

logging.basicConfig(level=logging.INFO, format="%(message)s")  # show INFO messages, without a prefix

var1 = "DetectMate getting started"
var2 = "what is a log"
logging.info(f"hello I am a log about {var1} and about {var2}")
```

produces the message:

```text
hello I am a log about DetectMate getting started and about what is a log
```

A log message can be split into two parts: a **static part** that stays the same
every time the message is logged, and a **variable part** that changes from one
log to the next.

Take this log line (from now on we refer to log messages as *lines*):

```text
User alice logged in from 192.168.0.5
```

The static parts here are `User` and `logged in from`, because they don't change across logging statements.
`alice` and `192.168.0.5` do change, as you can see in the next one:

```text
User bob logged in from 10.0.0.2
```

Now the name `alice` changed to `bob` for example.

In DetectMate the static part is called the **template**, and the placeholders
are marked with `<*>`. The variable parts are extracted into a separate list of
**variables**.

Logs often include a prefix with metadata, such as a timestamp, log level, or
hostname.

In plain terms: the **prefix** is just the part that comes first, before the
real message. The **metadata** is extra information *about* the log (when it
happened, how important it is, which machine sent it) rather than the message
itself. Think of it like the sender and date stamped on an envelope: useful to
know, but not the letter inside.
For example:

```text
INFO [18-05-2005] hello I am a log about DetectMate getting started and about what is a log
```

This line has three parts:

- **`INFO`: the category of the message (the "log level").** Some other
messages from the program could be for example `DEBUG` (fine-grained detail for developers) or `WARNING` (something looks off, but it's not a failure yet). So this part just gives you a hint how important this logging statement is.

- **`[18-05-2005]`: the timestamp,** i.e. when the message was written.

- **`hello I am a log...`: the actual text,** i.e. what the program wants to tell you.

The log level sits at the very front because it acts as a filter: in real systems thousands of lines pile up every second, so you can say e.g. "only show me `WARNING` and worse." That way both humans and machines can instantly decide whether a line is relevant.

## What is a parsed log?

A parsed log is a raw log that has been decomposed into structured fields: the
log is split at the right points and each part is labelled with what it is
(template, variables, timestamp, and so on).

The pattern that tells the parser how to split a line is called the
**`log_format`**. It names the fields in the order they appear in the raw line,
so the parser knows which chunk is the log level, which is the timestamp, and
which is the actual message content.

The term `log_format` is common in the log-parsing literature and is used by
tools such as the **Drain parser** and **LogParser**, among many others.

Based on the example above:

    log_format: <Level> [<Time>] <Content>
    template:   hello I am a log about <*> and about <*>

A parsed log would contain fields like:

| Field                | Value                                                  |
|----------------------|--------------------------------------------------------|
| `EventID`            | `0`                                                    |
| `template`           | `hello I am a log about <*> and about <*>`              |
| `variables`          | `["DetectMate getting started", "what is a log"]`      |
| `logFormatVariables` | `{"Level": "INFO", "Time": "18-05-2005", "Content": "hello I am a log about DetectMate getting started and about what is a log"}` |

Parsed logs expose structured data that downstream detection components use for
anomaly detection.

### What is an EventID?

Every distinct template is a different *kind* of event, and the parser gives
each one a number: the **`EventID`**. All lines that match the same template get
the same `EventID`, so `User alice logged in from 192.168.0.5` and
`User bob logged in from 10.0.0.2` share one `EventID`, while a
`User bob logged out` line would get another.

How the number is chosen depends on the parser. With the
[Template Matcher](../parsers/template_matcher.md), it is the position of the
matching template in your template file, counting from `0`: the first template is
`EventID 0`, the second `EventID 1`, and so on. In the table above the template
file contains just one template, so the line gets `EventID 0`. A line that
matches no template gets `EventID -1` and the template `<Not Found>`.

The `EventID` is what detectors build on:

- Detectors that watch variable values are configured per `EventID`: their
  `events` block says which variables to monitor for which kind of event (see
  [Detectors](../detectors.md#configuration)).
- Some detectors look at nothing but the `EventID`, for example the
  [New Event Detector](../detectors/new_event.md) (an `EventID` never seen
  before) and the [Event Sequence Detector](../detectors/event_sequence.md) (an
  unusual order of `EventID`s).

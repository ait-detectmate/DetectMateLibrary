# Basic Concepts

DetectMateLibrary is a collection of utilities for detecting anomalies in system logs. This short tutorial explains the core concepts you need to get started.

## What is a log?

Logs are messages produced by logging statements in code that describe events or states during execution.

Example code that produces a log:

```python
import logging

var1 = "DetectMate getting started"
var2 = "what is a log"

logging.info(f"hello I am a log about {var1} and about {var2}")
```

This produces the message:

```
hello I am a log about DetectMate getting started and about what is a log
```

A log message can be split into a constant part (the template) and variable parts, for example:

- Template: `hello I am a log about <*> and about <*>`
- Variables: `["DetectMate getting started", "what is a log"]`

Logs often include a prefix with metadata, such as time stamp, log level, or hostnamem, for example:

```
INFO [18-05-2005] hello I am a log about DetectMate getting started and about what is a log
```

To extract the metadata we define a log format. For the example above this would be:

```
<Level> [<Time>] <Content>
```

Using that format we can separate the message into the components log level `Level`, time stamp `Time`, and log message `Message`:

- Level: `INFO`
- Time: `18-05-2005`
- Message: `hello I am a log about DetectMate getting started and about what is a log`

## What is a parsed log?

A parsed log is a log that has been decomposed into structured fields. Based on the example above:

- log_format: `<Level> [<Time>] <Content>`
- template: `hello I am a log about <*> and about <*>`

A parsed log would contain fields like:

| Field              | Value                                                                 |
|--------------------|-----------------------------------------------------------------------|
| Template           | `hello I am a log about <*> and about <*>`                            |
| Variables          | `["DetectMate getting started", "what is a log"]`                     |
| LogFormatVariables | `{"Level": "INFO", "Time": "18-05-2005"}`                              |

Parsed logs expose structured data that downstream detection components use for anomaly detection.

Go back to [Index](index.md)

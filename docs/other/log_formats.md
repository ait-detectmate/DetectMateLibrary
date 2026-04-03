# Log Format Catalog

This catalog covers 18 common log formats and provides ready-to-use `log_format` patterns for the DetectMate parsers, such as the [MatcherParser](../parsers/template_matcher.md).

**Key concept:** `log_format` splits a raw log line into structured header fields that become entries in `ParserSchema.logFormatVariables`. The special `<Content>` token captures the variable message body, which is then matched against your template file to produce `EventID` and `variables`. Formats without `<Content>` are fully structured — no template file is needed.

**Generic configuration:**

```yaml
parsers:
  MyParser:
    method_type: matcher_parser
    auto_config: false
    log_format: "<Date> <Time> <Level> <Component>: <Content>"
    params:
      path_templates: path/to/templates.txt  # only required when log_format contains <Content>
```

---

## Quick Reference

| Format | Category | Log source | Has `<Content>` |
|--------|----------|------------|:--------------:|
| [audit](#audit) | Security | Linux auditd | yes |
| [ApacheAccess](#apacheaccess) | Web & Network | Apache httpd access log | no |
| [OpenSSH](#openssh) | Security | OpenSSH sshd | yes |
| [Apache](#apache) | Web & Network | Apache httpd error log | yes |
| [Proxifier](#proxifier) | Web & Network | Proxifier proxy client | yes |
| [HDFS](#hdfs) | Distributed Systems | Hadoop HDFS daemon | yes |
| [Hadoop](#hadoop) | Distributed Systems | Hadoop MapReduce | yes |
| [Spark](#spark) | Distributed Systems | Apache Spark | yes |
| [Zookeeper](#zookeeper) | Distributed Systems | Apache Zookeeper | yes |
| [OpenStack](#openstack) | Distributed Systems | OpenStack Nova/etc. | yes |
| [BGL](#bgl) | HPC / Supercomputers | IBM BlueGene/L | yes |
| [HPC](#hpc) | HPC / Supercomputers | Generic HPC cluster | yes |
| [Thunderbird](#thunderbird) | HPC / Supercomputers | Thunderbird supercomputer | yes |
| [Linux](#linux) | Operating Systems | Linux syslog / auth | yes |
| [Windows](#windows) | Operating Systems | Windows CBS/Setup | yes |
| [Mac](#mac) | Operating Systems | macOS system log | yes |
| [Android](#android) | Operating Systems | Android logcat | yes |
| [HealthApp](#healthapp) | Application | Mobile health app | yes |

---

## Security

### audit

Linux auditd log. Produced by the kernel audit subsystem; records system calls, authentication, and policy events.

```text
type=USER_ACCT msg=audit(1642723741.072:375): pid=10125 uid=0 auid=4294967295 ses=4294967295 msg='op=PAM:accounting acct="root" exe="/usr/sbin/cron" hostname=? addr=? terminal=cron res=success'
```

**`log_format`:** `type=<Type> msg=audit(<Time>): <Content>`

**Variable noise patterns:** Numeric field values (`=\d+`), IP addresses (`(\d+\.){3}\d+`).

---

### OpenSSH

OpenSSH `sshd` authentication log. Records login attempts, key exchanges, and session events.

```text
Dec 10 07:07:38 LabSZ sshd[24206]: Failed password for invalid user test9 from 192.168.1.1 port 20992 ssh2
```

**`log_format`:** `<Date> <Day> <Time> <Component> sshd[<Pid>]: <Content>`

**Variable noise patterns:** IP addresses (`(\d+\.){3}\d+`), hostnames (`([\w-]+\.){2,}[\w-]+`).

---

## Web & Network

### ApacheAccess

Apache httpd access log (Combined Log Format). Each line is fully structured — no template file is required.

```text
64.242.88.10 - - [07/Mar/2004:16:10:02 -0800] "GET /twiki/bin/edit/Main/Double_bounce_sender?topicparent=Main.ConfigurationVariables HTTP/1.1" 401 12846 "-" "Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.2) Gecko/20021202"
```

**`log_format`:** `<IP> - - [<Time>] "<RequestType> <Request> <Version>" <Status> <ResponseSize> "<Referer>" "<UserAgent>"`

> All fields land directly in `logFormatVariables`. Use `header_variables` in your detector config to track e.g. `Status`, `IP`, or `RequestType`.

---

### Apache

Apache httpd error log. Records server errors, warnings, and informational notices.

```text
[Sun Dec 04 04:47:44 2005] [notice] workerEnv.init() ok /etc/httpd/conf/workers2.properties
```

**`log_format`:** `[<Time>] [<Level>] <Content>`

**Variable noise patterns:** IP addresses (`(\d+\.){3}\d+`).

---

### Proxifier

Proxifier proxy client log. Records connection open/close events with traffic statistics.

```text
[10:39:55] Skype.exe - www.bing.com:443 open through proxy 1.2.3.4:8080 OK
```

**`log_format`:** `[<Time>] <Program> - <Content>`

**Variable noise patterns:** Duration values (`<\d+\ssec`), domain:port pairs (`([\w-]+\.)+[\w-]+(:\d+)?`), transfer sizes (`[KGTM]B`).

---

## Distributed Systems

### HDFS

Hadoop Distributed File System daemon log. Emitted by DataNodes, NameNodes, and other HDFS services.

```text
081109 203518 148 INFO dfs.DataNode$DataXceiver: Receiving block blk_-1608999687919862906 src: /10.251.73.220:54106 dest: /10.251.73.220:50010
```

**`log_format`:** `<Date> <Time> <Pid> <Level> <Component>: <Content>`

**Variable noise patterns:** HDFS block IDs (`blk_-?\d+`), IP addresses with optional port (`(\d+\.){3}\d+(:\d+)?`).

---

### Hadoop

Hadoop MapReduce / YARN log. Produced by the ResourceManager, NodeManager, and application containers.

```text
2015-10-17 15:37:15,811 INFO [main] org.apache.hadoop.mapreduce.v2.app.MRAppMaster: Created MRAppMaster for application appattempt_1443144491176_0001_000001
```

**`log_format`:** `<Date> <Time> <Level> [<Process>] <Component>: <Content>`

**Variable noise patterns:** IP addresses (`(\d+\.){3}\d+`).

---

### Spark

Apache Spark log. Emitted by driver and executor JVMs.

```text
15/10/16 03:35:11 INFO storage.BlockManagerMasterActor: Registering block manager 192.168.1.1:61698 with 896.4 MB RAM, BlockManagerId(1, 192.168.1.1, 61698)
```

**`log_format`:** `<Date> <Time> <Level> <Component>: <Content>`

**Variable noise patterns:** IP addresses, memory size units (`\b[KGTM]?B\b`), domain-like names (`([\w-]+\.){2,}[\w-]+`).

---

### Zookeeper

Apache Zookeeper log. Produced by quorum peers and server threads.

```text
2015-07-29 17:37:13,090 - INFO  [QuorumPeer:NIOServerCnxn@943] - Closed socket connection for client /192.168.1.8:56613 which had sessionid 0x14eb8e0aac70006
```

**`log_format`:** `<Date> <Time> - <Level>  [<Node>:<Component>@<Id>] - <Content>`

**Variable noise patterns:** IP addresses with optional port (`(/|)(\d+\.){3}\d+(:\d+)?`).

---

### OpenStack

OpenStack service log (Nova, Neutron, etc.). Structured with a request context field.

```text
nova-manage.log 2016-09-28 03:51:11.899 25746 INFO nova.metadata.handler [req-5a1f3f8a-fd7a-4dc5-bb32-f642b2de2e74 - - - - -] 127.0.0.1 "GET /openstack/2012-08-10/meta-data/local-ipv4" status: 200 len: 14 time: 0.007720
```

**`log_format`:** `<Logrecord> <Date> <Time> <Pid> <Level> <Component> [<ADDR>] <Content>`

**Variable noise patterns:** IP addresses (`((\d+\.){3}\d+,?)+`), file paths (`/.+?\s`), numeric values (`\d+`).

---

## HPC / Supercomputers

### BGL

IBM BlueGene/L supercomputer log. Contains hardware-level diagnostic messages with node location identifiers.

```text
- 1117838570 2005.06.03 R02-M1-N0-C:J12-U11 2005-06-03-15.42.50.363779 R02-M1-N0-C:J12-U11 RAS KERNEL INFO instruction cache parity error corrected
```

**`log_format`:** `<Label> <Timestamp> <Date> <Node> <Time> <NodeRepeat> <Type> <Component> <Level> <Content>`

**Variable noise patterns:** Core dump references (`core\.\d+`).

---

### HPC

Generic HPC cluster log. Produced by batch schedulers and system daemons on compute nodes.

```text
5 hpc-lnx-node11 afs RUNNING 1169880007 OK File transfer: 23 files copied 0 bytes in 0.000 secs
```

**`log_format`:** `<LogId> <Node> <Component> <State> <Time> <Flag> <Content>`

**Variable noise patterns:** Numeric assignments (`=\d+`).

---

### Thunderbird

Thunderbird supercomputer log. Similar to BGL but from a different cluster; includes user and location fields.

```text
- 1131566401 2005.11.09 admin Nov 9 21:00:01 tbird1 crond[3049]: (root) CMD (/usr/lib/sa/sa1 1 1)
```

**`log_format`:** `<Label> <Timestamp> <Date> <User> <Month> <Day> <Time> <Location> <Component>([<PID>])?: <Content>`

**Variable noise patterns:** IP addresses (`(\d+\.){3}\d+`).

---

## Operating Systems

### Linux

Linux syslog format (RFC 3164). Produced by `syslog`, `rsyslog`, and `syslog-ng` — covers auth, cron, kernel messages, and more.

```text
Jun 14 15:16:02 combo sshd(pam_unix)[19939]: authentication failure; logname= uid=0 euid=0 tty=NODEVssh ruser= rhost=218.188.2.4
```

**`log_format`:** `<Month> <Date> <Time> <Level> <Component>([<PID>])?: <Content>`

> Note: `<Level>` captures the **hostname** in standard syslog (the field name follows benchmark convention).

**Variable noise patterns:** IP addresses (`(\d+\.){3}\d+`), embedded timestamps (`\d{2}:\d{2}:\d{2}`).

---

### Windows

Windows Component-Based Servicing (CBS) / Setup log. Fixed-width columns with variable spacing.

```text
2016-09-28 04:30:22, Info                  CBS    Loaded Servicing Stack v6.1.7601.23505 with Core: C:\Windows\winsxs\amd64_microsoft-windows-servicingstack_31bf3856ad364e35_6.1.7601.23505_none_681aa442f6fed7f0\cbscore.dll
```

**`log_format`:** `<Date> <Time>, <Level>                  <Component>    <Content>`

> Note: The multiple spaces between fields are **literal** and must be preserved in the pattern.

**Variable noise patterns:** Hexadecimal values (`0x.*?\s`).

---

### Mac

macOS unified system log (pre-Unified Logging). Produced by system daemons and user-space processes.

```text
Jul  9 00:17:03 calvisitor-10-105-160-95 com.apple.backupd[12396] (Error): VSDBUtil: Failed to change_attributes for volume "/Volumes/SanDisk USB Drive"
```

**`log_format`:** `<Month>  <Date> <Time> <User> <Component>[<PID>]( (<Address>))?: <Content>`

> Note: Double space between `<Month>` and `<Date>` occurs when the day is single-digit (standard macOS padding).

**Variable noise patterns:** Domain names (`([\w-]+\.){2,}[\w-]+`).

---

### Android

Android logcat output. Produced by the Android logging system across all framework and app components.

```text
01-02 12:23:42.768  1632  2044 E ActivityManager: mDVFSHelper is null
```

**`log_format`:** `<Date> <Time>  <Pid>  <Tid> <Level> <Component>: <Content>`

**Variable noise patterns:** File system paths (`(/[\w-]+)+`), domain names, hex/numeric values (`\b(\-?\+?\d+)\b|\b0[Xx][a-fA-F\d]+\b|\b[a-fA-F\d]{4,}\b`).

---

## Application

### HealthApp

Mobile health application log. Pipe-delimited format from a step-counter app.

```text
20170201-01:15:35:631|Step_StandCounter|4243|step counts since boot=76149; goal=6000; active=0; distance=45
```

**`log_format`:** `<Time>|<Component>|<Pid>|<Content>`

---

Go back to [Index](../index.md)

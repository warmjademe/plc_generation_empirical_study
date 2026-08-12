# C05_M02_heartbeat_watchdog: Heartbeat watchdog timeout

## Objective

Implement `C05_M02_heartbeat_watchdog` as an IEC-ST Core v1 function block in the Timers and timeouts category. Preserve the supplied interface exactly.

## Requirements

- **R1**: While monitoring, a Heartbeat shall restart the 400 ms watchdog interval.
- **R2** **[safety-critical]**: Absence of Heartbeat for at least 400 ms shall latch TimedOut TRUE.
- **R3**: Reset shall clear TimedOut only while MonitorEnable is FALSE.
- **R4**: Healthy shall equal MonitorEnable and not TimedOut.

## Assumptions

- The runtime scan period is 100 ms.
- Heartbeat is a pulse lasting no more than one scan.
- Each test starts from a fresh function-block instance.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

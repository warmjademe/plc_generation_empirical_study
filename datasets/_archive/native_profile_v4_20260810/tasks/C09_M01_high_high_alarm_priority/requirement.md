# C09_M01_high_high_alarm_priority: High and high-high alarm priority

## Objective

Implement `C09_M01_high_high_alarm_priority` as an IEC-ST Core v1 function block in the Alarms and fault recovery category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Value at or above HighLimit shall latch HighAlarm.
- **R2** **[safety-critical]**: Value at or above HighHighLimit shall latch both alarms and Shutdown.
- **R3**: A high alarm below HighHighLimit shall not by itself assert Shutdown.
- **R4**: Reset shall clear all latched outputs only below HighLimit.

## Assumptions

- HighHighLimit is greater than HighLimit.
- Each test starts from a fresh function-block instance.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

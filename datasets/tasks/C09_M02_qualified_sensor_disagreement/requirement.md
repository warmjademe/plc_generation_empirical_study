# C09_M02_qualified_sensor_disagreement: Time-qualified sensor disagreement alarm

## Objective

Implement `C09_M02_qualified_sensor_disagreement` as an IEC-ST Core v1 function block in the Alarms and fault recovery category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Disagreeing shall be TRUE exactly when monitoring is enabled and the absolute difference exceeds MaxDifference.
- **R2**: A disagreement lasting 300 ms shall latch Alarm.
- **R3**: A shorter disagreement shall not latch Alarm.
- **R4**: Reset shall clear Alarm only while no disagreement is present.

## Assumptions

- The runtime scan period is 100 ms.
- MaxDifference is non-negative.
- Each test starts from a fresh function-block instance.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

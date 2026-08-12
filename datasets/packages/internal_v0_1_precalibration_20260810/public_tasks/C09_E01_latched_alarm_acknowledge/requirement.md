# C09_E01_latched_alarm_acknowledge: Latched alarm with acknowledge and reset

## Objective

Implement `C09_E01_latched_alarm_acknowledge` as an IEC-ST Core v1 function block in the Alarms and fault recovery category. Preserve the supplied interface exactly.

## Requirements

- **R1**: AlarmCondition shall latch AlarmActive and AlarmUnacked TRUE.
- **R2**: Acknowledge may clear AlarmUnacked while AlarmActive remains latched.
- **R3**: Reset shall clear both outputs only while AlarmCondition is FALSE.

## Assumptions

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

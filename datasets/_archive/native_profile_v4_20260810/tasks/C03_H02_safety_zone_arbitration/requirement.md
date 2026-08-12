# C03_H02_safety_zone_arbitration: Safety-zone actuator arbitration

## Objective

Implement `C03_H02_safety_zone_arbitration` as an IEC-ST Core v1 function block in the Interlocks and safe outputs category. Preserve the supplied interface exactly.

## Requirements

- **R1** **[safety-critical]**: Loss of GuardClosed or EStopOK shall disable all grants.
- **R2** **[safety-critical]**: Authorized ManualRequest has highest priority.
- **R3**: RobotRequest has priority over ConveyorRequest when manual mode is not granted.
- **R4** **[safety-critical]**: At most one grant shall be TRUE.
- **R5**: Conflict shall indicate more than one eligible request before arbitration.

## Assumptions

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

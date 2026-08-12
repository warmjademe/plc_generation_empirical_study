# C03_M02_heating_cooling_deadband: Mutually exclusive heating and cooling with deadband

## Objective

Implement `C03_M02_heating_cooling_deadband` as an IEC-ST Core v1 function block in the Interlocks and safe outputs category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Heat shall turn on below Setpoint minus 1.0 while enabled and safe.
- **R2**: Cool shall turn on above Setpoint plus 1.0 while enabled and safe.
- **R3**: Neither output shall be active inside the inclusive deadband.
- **R4** **[safety-critical]**: Heat and Cool shall never be active together, and SafetyTrip shall turn both off.

## Assumptions

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

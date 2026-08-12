# C03_M01_pump_valve_interlock: Pump and discharge-valve interlock

## Objective

Implement `C03_M01_pump_valve_interlock` as an IEC-ST Core v1 function block in the Interlocks and safe outputs category. Preserve the supplied interface exactly.

## Requirements

- **R1**: ValveCommand shall follow a valid RunRequest while TankLevelOK and not Stop hold.
- **R2** **[safety-critical]**: PumpCommand requires ValveFeedbackOpen in addition to the valve-command permissives.
- **R3** **[safety-critical]**: PumpCommand shall be FALSE when Stop or loss of TankLevelOK is active.
- **R4** **[safety-critical]**: InterlockAlarm shall be TRUE when PumpFeedback is TRUE while valve feedback is closed.

## Assumptions

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

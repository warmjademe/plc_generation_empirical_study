# C02_X01_restart_inhibit_latch: Mode-selected start latch with restart inhibit

## Objective

Implement `C02_X01_restart_inhibit_latch` as an IEC-ST Core v1 function block in the Start/stop and retained state category. Preserve the supplied interface exactly.

## Requirements

- **R1**: AutoMode shall select AutoStart; manual mode shall select ManualStart.
- **R2** **[safety-critical]**: Stop, Enable FALSE, or SafetyOK FALSE shall force Running FALSE with priority over every start.
- **R3** **[safety-critical]**: Safety loss while running or while a start is requested shall latch RestartRequired.
- **R4**: RestartRequired may clear only when Reset is TRUE, SafetyOK and Enable are TRUE, and the selected start is released.
- **R5** **[safety-critical]**: A start presented while RestartRequired is TRUE shall not run and shall pulse RejectedStart.
- **R6**: With all permissions healthy and no restart inhibit, a selected start shall latch Running until a stop condition occurs.

## Assumptions

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

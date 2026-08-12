# C03_X01_ventilated_heater_interlock: Ventilated heater startup with proof timeout

## Objective

Implement `C03_X01_ventilated_heater_interlock` as an IEC-ST Core v1 function block in the Interlocks and safe outputs category. Preserve the supplied interface exactly.

## Requirements

- **R1**: A healthy HeatRequest shall enter ventilation proving and command the damper and fan before the heater.
- **R2** **[safety-critical]**: HeaterCommand may energize only after DamperOpen and AirflowOK remain TRUE for 300 ms.
- **R3** **[safety-critical]**: Failure to establish both proofs within 600 ms shall latch Fault and force all commands FALSE.
- **R4** **[safety-critical]**: Loss of GuardClosed, DamperOpen, or AirflowOK while heating shall immediately trip and latch Fault.
- **R5**: Stop shall return to idle without clearing Fault; Reset clears Fault only while idle with HeatRequest FALSE.
- **R6** **[safety-critical]**: HeaterCommand shall never be TRUE unless DamperCommand and FanCommand are both TRUE.

## Assumptions

- The runtime scan period is 100 ms.
- Proof inputs are sampled at scan start.
- Each test starts from a fresh function-block instance.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

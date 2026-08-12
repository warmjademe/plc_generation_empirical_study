# C01_M02_mode_dependent_command: Mode-dependent command selection

## Objective

Implement `C01_M02_mode_dependent_command` as an IEC-ST Core v1 function block in the Boolean and conditional logic category. Preserve the supplied interface exactly.

## Requirements

- **R1** **[safety-critical]**: Command shall follow AutoDemand in automatic mode and ManualDemand in manual mode, but only when SafetyOK is TRUE and Inhibit is FALSE.
- **R2**: Blocked shall be TRUE when the selected request is TRUE but safety is not OK or Inhibit is TRUE.

## Assumptions

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

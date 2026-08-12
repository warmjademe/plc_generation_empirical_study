# C02_H02_safe_restart_inhibit: Safe restart after power or safety interruption

## Objective

Implement `C02_H02_safe_restart_inhibit` as an IEC-ST Core v1 function block in the Start/stop and retained state category. Preserve the supplied interface exactly.

## Requirements

- **R1** **[safety-critical]**: Loss of PowerOK or SafetyOK shall stop Running and set RestartInhibit.
- **R2** **[safety-critical]**: Stop shall stop Running without by itself setting RestartInhibit.
- **R3**: Reset may clear RestartInhibit only when PowerOK and SafetyOK are TRUE and Start is FALSE.
- **R4** **[safety-critical]**: Running shall remain FALSE while RestartInhibit is TRUE.
- **R5**: After reset, a new Start may run the machine when PowerOK, SafetyOK, and not Stop hold.

## Assumptions

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

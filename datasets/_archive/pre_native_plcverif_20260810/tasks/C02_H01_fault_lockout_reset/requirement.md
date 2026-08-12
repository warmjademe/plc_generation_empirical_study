# C02_H01_fault_lockout_reset: Fault lockout with qualified manual reset

## Objective

Implement `C02_H01_fault_lockout_reset` as an IEC-ST Core v1 function block in the Start/stop and retained state category. Preserve the supplied interface exactly.

## Requirements

- **R1** **[safety-critical]**: Fault shall immediately stop Running and latch LockedOut TRUE.
- **R2**: Reset shall clear LockedOut only when Fault is FALSE and Start is FALSE.
- **R3** **[safety-critical]**: Start shall not run the equipment while LockedOut, Stop, or loss of Permit is active.
- **R4** **[safety-critical]**: Clearing the lockout shall not automatically restart the equipment.
- **R5**: A new Start after a successful reset may latch Running TRUE.

## Assumptions

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

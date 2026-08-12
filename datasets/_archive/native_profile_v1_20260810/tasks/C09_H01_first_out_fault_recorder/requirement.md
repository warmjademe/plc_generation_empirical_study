# C09_H01_first_out_fault_recorder: First-out fault recorder with deterministic priority

## Objective

Implement `C09_H01_first_out_fault_recorder` as an IEC-ST Core v1 function block in the Alarms and fault recovery category. Preserve the supplied interface exactly.

## Requirements

- **R1**: AnyFault shall equal the disjunction of all three fault inputs.
- **R2** **[safety-critical]**: The first observed fault shall latch LockedOut and its code in FirstFault.
- **R3**: Simultaneous first faults shall use priority A, then B, then C.
- **R4**: Later faults shall not overwrite FirstFault while LockedOut is TRUE.
- **R5**: Reset shall clear LockedOut and FirstFault only when all fault inputs are FALSE.

## Assumptions

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

# C01_H01_four_level_priority: Four-level alarm priority encoder

## Objective

Implement `C01_H01_four_level_priority` as an IEC-ST Core v1 function block in the Boolean and conditional logic category. Preserve the supplied interface exactly.

## Requirements

- **R1** **[safety-critical]**: Emergency shall always produce Level 4 and Active TRUE, even when Suppress is TRUE.
- **R2**: When not suppressed, the highest active condition shall determine Level.
- **R3**: Suppress shall force Level 0 and Active FALSE when Emergency is FALSE.
- **R4**: Level 0 shall be equivalent to Active FALSE.

## Assumptions

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

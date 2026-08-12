# C01_M01_two_out_of_three_vote: Two-out-of-three sensor voter

## Objective

Implement `C01_M01_two_out_of_three_vote` as an IEC-ST Core v1 function block in the Boolean and conditional logic category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Vote shall be TRUE when at least two of S1, S2, and S3 are TRUE.
- **R2**: Unanimous shall be TRUE only when all three channels have the same value.

## Assumptions

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

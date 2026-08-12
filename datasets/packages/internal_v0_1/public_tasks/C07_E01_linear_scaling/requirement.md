# C07_E01_linear_scaling: Linear raw-value scaling

## Objective

Implement `C07_E01_linear_scaling` as an IEC-ST Core v1 function block in the Analog processing category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Engineering shall equal Raw multiplied by 0.1 for Raw values from 0 through 1000.

## Assumptions

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

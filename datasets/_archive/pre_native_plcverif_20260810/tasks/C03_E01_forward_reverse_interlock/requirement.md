# C03_E01_forward_reverse_interlock: Forward/reverse motor interlock

## Objective

Implement `C03_E01_forward_reverse_interlock` as an IEC-ST Core v1 function block in the Interlocks and safe outputs category. Preserve the supplied interface exactly.

## Requirements

- **R1** **[safety-critical]**: Forward shall be TRUE only for an exclusive forward request with Permit TRUE.
- **R2** **[safety-critical]**: Reverse shall be TRUE only for an exclusive reverse request with Permit TRUE.
- **R3** **[safety-critical]**: Forward and Reverse shall never be TRUE together.

## Assumptions

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

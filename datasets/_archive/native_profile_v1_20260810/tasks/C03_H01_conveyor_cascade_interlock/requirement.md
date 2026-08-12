# C03_H01_conveyor_cascade_interlock: Three-conveyor downstream interlock

## Objective

Implement `C03_H01_conveyor_cascade_interlock` as an IEC-ST Core v1 function block in the Interlocks and safe outputs category. Preserve the supplied interface exactly.

## Requirements

- **R1** **[safety-critical]**: C3Run shall require RunRequest, C3Available, C3Clear, and not Stop.
- **R2** **[safety-critical]**: C2Run shall require C3Run, C2Available, and C2Clear.
- **R3** **[safety-critical]**: C1Run shall require C2Run and C1Clear.
- **R4** **[safety-critical]**: Stop shall turn all three commands off.
- **R5**: Blocked shall indicate RunRequest with at least one unavailable or uncleared stage.

## Assumptions

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

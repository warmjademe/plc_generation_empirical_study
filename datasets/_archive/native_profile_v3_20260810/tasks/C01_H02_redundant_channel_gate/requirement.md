# C01_H02_redundant_channel_gate: Redundant-channel safety gate

## Objective

Implement `C01_H02_redundant_channel_gate` as an IEC-ST Core v1 function block in the Boolean and conditional logic category. Preserve the supplied interface exactly.

## Requirements

- **R1** **[safety-critical]**: Disagree shall be TRUE exactly when ChA and ChB differ.
- **R2** **[safety-critical]**: Normal SafeEnable requires ProcessRequest and both channels TRUE.
- **R3** **[safety-critical]**: Test mode may bypass ChB only when TestPermit and ChA are TRUE.
- **R4**: TestActive shall indicate TestMode and TestPermit together.

## Assumptions

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

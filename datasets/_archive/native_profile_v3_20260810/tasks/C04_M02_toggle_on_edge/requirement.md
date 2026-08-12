# C04_M02_toggle_on_edge: Toggle output on qualified rising edge

## Objective

Implement `C04_M02_toggle_on_edge` as an IEC-ST Core v1 function block in the Edge and event handling category. Preserve the supplied interface exactly.

## Requirements

- **R1** **[safety-critical]**: Reset shall clear State and suppress AcceptedPulse with highest priority.
- **R2**: A rising Button edge while Enable is TRUE shall invert State exactly once.
- **R3**: Holding Button TRUE shall not repeatedly toggle State.

## Assumptions

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

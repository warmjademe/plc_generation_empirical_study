# C04_E01_rising_edge_pulse: Single-scan rising-edge pulse

## Objective

Implement `C04_E01_rising_edge_pulse` as an IEC-ST Core v1 function block in the Edge and event handling category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Pulse shall be TRUE for the scan in which Signal changes from FALSE to TRUE.
- **R2**: Pulse shall be FALSE while Signal remains TRUE or remains FALSE.

## Assumptions

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

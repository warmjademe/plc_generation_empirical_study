# C04_M01_falling_edge_pulse: Armed falling-edge pulse

## Objective

Implement `C04_M01_falling_edge_pulse` as an IEC-ST Core v1 function block in the Edge and event handling category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Armed shall equal Arm at the end of each scan.
- **R2**: Pulse shall occur on a TRUE-to-FALSE Signal transition only when Arm is TRUE.
- **R3**: Disarming shall suppress Pulse without corrupting future edge detection.

## Assumptions

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

# C07_M01_clamped_scaling: Clamped analog scaling with range status

## Objective

Implement `C07_M01_clamped_scaling` as an IEC-ST Core v1 function block in the Analog processing category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Raw below zero shall set UnderRange, clear OverRange, and clamp Engineering to 0.0.
- **R2**: Raw above 4095 shall set OverRange, clear UnderRange, and clamp Engineering to 10.0.
- **R3**: In-range Raw shall clear both flags and scale linearly to 0.0 through 10.0.

## Assumptions

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

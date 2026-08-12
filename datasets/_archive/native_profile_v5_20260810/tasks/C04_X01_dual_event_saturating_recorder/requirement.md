# C04_X01_dual_event_saturating_recorder: Qualified dual-edge recorder with saturation and re-arm

## Objective

Implement `C04_X01_dual_event_saturating_recorder` as an IEC-ST Core v1 function block in the Edge and event handling category. Preserve the supplied interface exactly.

## Requirements

- **R1** **[safety-critical]**: Only a qualified, non-inhibited rising edge observed while not previously locked may be accepted.
- **R2** **[safety-critical]**: Simultaneous eligible edges shall accept A only.
- **R3**: Each accepted event increments Count once and records LastSource.
- **R4** **[safety-critical]**: Except for a qualified reset scan, Count shall saturate at MaxCount and latch Locked; MaxCount less than or equal to zero locks without counting.
- **R5**: A held-high event shall not retrigger until observed low and then rising again.
- **R6**: Reset clears Count, Locked, and LastSource only while both events are low.

## Assumptions

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.
- MaxCount remains constant during a test.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

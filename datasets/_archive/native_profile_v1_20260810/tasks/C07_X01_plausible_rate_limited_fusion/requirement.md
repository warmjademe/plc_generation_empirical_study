# C07_X01_plausible_rate_limited_fusion: Redundant sensor fusion with plausibility and rate trip

## Objective

Implement `C07_X01_plausible_rate_limited_fusion` as an IEC-ST Core v1 function block in the Analog processing category. Preserve the supplied interface exactly.

## Requirements

- **R1**: When both sensors are valid and their absolute difference is at most MaxDifference, the candidate value is their average.
- **R2**: When exactly one sensor is valid, the candidate is that sensor and Degraded is TRUE.
- **R3** **[safety-critical]**: When both valid sensors differ by more than MaxDifference, Disagree is TRUE and ValidOutput is FALSE.
- **R4** **[safety-critical]**: After initialization, an otherwise valid candidate changing by more than MaxRate shall latch RateTrip and shall not replace ProcessValue.
- **R5** **[safety-critical]**: RateTrip or Enable FALSE shall force ValidOutput FALSE; Reset clears RateTrip only while disabled.
- **R6**: At equality boundaries for MaxDifference and MaxRate, the candidate remains acceptable.

## Assumptions

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

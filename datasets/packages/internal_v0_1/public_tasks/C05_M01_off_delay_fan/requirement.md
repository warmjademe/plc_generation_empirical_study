# C05_M01_off_delay_fan: Off-delay ventilation fan

## Objective

Implement `C05_M01_off_delay_fan` as an IEC-ST Core v1 function block in the Timers and timeouts category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Fan shall turn on without delay when Demand becomes TRUE and SafetyTrip is FALSE.
- **R2**: After Demand becomes FALSE, Fan shall remain on for 300 ms unless SafetyTrip occurs.
- **R3** **[safety-critical]**: SafetyTrip shall turn Fan and RunOn off immediately.
- **R4**: RunOn shall indicate the interval in which Demand is FALSE but the off-delay output remains TRUE.

## Assumptions

- The runtime scan period is 100 ms.
- Demand is held TRUE for at least one scan before an off-delay test.
- Each test starts from a fresh function-block instance.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

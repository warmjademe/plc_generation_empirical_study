# C10_X01_three_pump_feedback_dispatch: Three-pump staged dispatch with lead preference and feedback exclusion

## Objective

Implement `C10_X01_three_pump_feedback_dispatch` as an IEC-ST Core v1 function block in the Multi-device coordination category. Preserve the supplied interface exactly.

## Requirements

- **R1**: LowDemand shall request one pump and HighDemand shall request two, with HighDemand taking priority.
- **R2**: Dispatch shall prefer Lead, then the next pump numbers cyclically, excluding unavailable or feedback-failed pumps.
- **R3** **[safety-critical]**: A commanded pump without feedback for 300 ms shall be excluded and replaced when capacity permits.
- **R4** **[safety-critical]**: ActiveCount shall equal the number of TRUE run outputs, and no more than two pumps may run.
- **R5** **[safety-critical]**: Failover shall be TRUE when an unhealthy preferred pump is bypassed or requested capacity cannot be met; insufficient capacity shall latch Fault.
- **R6** **[safety-critical]**: Stop shall immediately clear every run command; Reset clears failures only while both demand inputs and Stop are FALSE.

## Assumptions

- The runtime scan period is 100 ms.
- At most two pumps are required simultaneously.
- Each test starts from a fresh function-block instance.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

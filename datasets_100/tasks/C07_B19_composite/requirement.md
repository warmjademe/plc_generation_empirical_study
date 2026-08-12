# C07_B19_composite: Composed supervisory control: Redundant sensor fusion with plausibility and rate trip -> Clamped analog scaling with range status

## Objective

Implement `C07_B19_composite` as an IEC-ST Core v1 function block in the Analog processing category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: When both sensors are valid and their absolute difference is at most A_MaxDifference, the A_Candidate value is their average.
- **R2**: Subsystem A shall satisfy: When exactly one sensor is valid, the A_Candidate is that sensor and A_Degraded is TRUE.
- **R3** **[safety-critical]**: Subsystem A shall satisfy: When both valid sensors differ by more than A_MaxDifference, A_Disagree is TRUE and A_ValidOutput is FALSE.
- **R4** **[safety-critical]**: Subsystem A shall satisfy: After initialization, an otherwise valid A_Candidate changing by more than A_MaxRate shall latch A_RateTrip and shall not replace A_ProcessValue.
- **R5** **[safety-critical]**: Subsystem A shall satisfy: A_RateTrip or A_Enable FALSE shall force A_ValidOutput FALSE; A_Reset clears A_RateTrip only while disabled.
- **R6**: Subsystem A shall satisfy: At equality boundaries for A_MaxDifference and A_MaxRate, the A_Candidate remains acceptable.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Raw below zero shall set B_UnderRange, clear B_OverRange, and clamp B_Engineering to 0.0.
- **R8**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Raw above 4095 shall set B_OverRange, clear B_UnderRange, and clamp B_Engineering to 10.0.
- **R9**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: In-range B_Raw shall clear both flags and scale linearly to 0.0 through 10.0.
- **R10** **[safety-critical]**: A TRUE A_ValidOutput shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R11** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R12**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R13** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- Subsystem A: The function block is called exactly once per PLC scan.
- Subsystem A: Inputs are sampled at scan start and outputs are checked at scan end.
- Subsystem A: Each test starts from a fresh function-block instance.
- Subsystem B: The function block is called exactly once per PLC scan.
- Subsystem B: Inputs are sampled at scan start and outputs are checked at scan end.
- Subsystem B: Each test starts from a fresh function-block instance.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

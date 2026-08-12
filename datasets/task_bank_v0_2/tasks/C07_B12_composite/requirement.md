# C07_B12_composite: Composed supervisory control: Clamped analog scaling with range status -> Redundant sensor fusion with plausibility and rate trip

## Objective

Implement `C07_B12_composite` as an IEC-ST Core v1 function block in the Analog processing category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A_Raw below zero shall set A_UnderRange, clear A_OverRange, and clamp A_Engineering to 0.0.
- **R2**: Subsystem A shall satisfy: A_Raw above 4095 shall set A_OverRange, clear A_UnderRange, and clamp A_Engineering to 10.0.
- **R3**: Subsystem A shall satisfy: In-range A_Raw shall clear both flags and scale linearly to 0.0 through 10.0.
- **R4**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: When both sensors are valid and their absolute difference is at most B_MaxDifference, the B_Candidate value is their average.
- **R5**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: When exactly one sensor is valid, the B_Candidate is that sensor and B_Degraded is TRUE.
- **R6** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: When both valid sensors differ by more than B_MaxDifference, B_Disagree is TRUE and B_ValidOutput is FALSE.
- **R7** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: After initialization, an otherwise valid B_Candidate changing by more than B_MaxRate shall latch B_RateTrip and shall not replace B_ProcessValue.
- **R8** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_RateTrip or B_Enable FALSE shall force B_ValidOutput FALSE; B_Reset clears B_RateTrip only while disabled.
- **R9**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: At equality boundaries for B_MaxDifference and B_MaxRate, the B_Candidate remains acceptable.
- **R10** **[safety-critical]**: A TRUE A_UnderRange shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R11** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R12**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R13** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

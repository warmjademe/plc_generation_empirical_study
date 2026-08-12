# C07_B18_composite: Composed supervisory control: Redundant sensor fusion with plausibility and rate trip -> Rate-of-change monitoring with latched trip

## Objective

Implement `C07_B18_composite` as an IEC-ST Core v1 function block in the Analog processing category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: When both sensors are valid and their absolute difference is at most A_MaxDifference, the A_Candidate value is their average.
- **R2**: Subsystem A shall satisfy: When exactly one sensor is valid, the A_Candidate is that sensor and A_Degraded is TRUE.
- **R3** **[safety-critical]**: Subsystem A shall satisfy: When both valid sensors differ by more than A_MaxDifference, A_Disagree is TRUE and A_ValidOutput is FALSE.
- **R4** **[safety-critical]**: Subsystem A shall satisfy: After initialization, an otherwise valid A_Candidate changing by more than A_MaxRate shall latch A_RateTrip and shall not replace A_ProcessValue.
- **R5** **[safety-critical]**: Subsystem A shall satisfy: A_RateTrip or A_Enable FALSE shall force A_ValidOutput FALSE; A_Reset clears A_RateTrip only while disabled.
- **R6**: Subsystem A shall satisfy: At equality boundaries for A_MaxDifference and A_MaxRate, the A_Candidate remains acceptable.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: The first enabled sample shall initialize history, set B_Ready, and shall not B_Trip.
- **R8**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: For subsequent enabled samples, B_Delta shall equal B_Value minus the B_Previous enabled B_Value.
- **R9** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: A B_Delta above B_MaxRise or below negative B_MaxFall shall latch B_Trip.
- **R10** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Trip shall remain set until B_Reset occurs while B_Enable is FALSE.
- **R11**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Disabling monitoring shall clear B_Ready but shall not by itself clear B_Trip.
- **R12** **[safety-critical]**: A TRUE A_ValidOutput shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R13** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R14**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R15** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

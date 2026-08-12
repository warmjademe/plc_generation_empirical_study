# C07_B17_composite: Composed supervisory control: Redundant sensor fusion with plausibility and rate trip -> Redundant analog sensor selection

## Objective

Implement `C07_B17_composite` as an IEC-ST Core v1 function block in the Analog processing category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: When both sensors are valid and their absolute difference is at most A_MaxDifference, the A_Candidate value is their average.
- **R2**: Subsystem A shall satisfy: When exactly one sensor is valid, the A_Candidate is that sensor and A_Degraded is TRUE.
- **R3** **[safety-critical]**: Subsystem A shall satisfy: When both valid sensors differ by more than A_MaxDifference, A_Disagree is TRUE and A_ValidOutput is FALSE.
- **R4** **[safety-critical]**: Subsystem A shall satisfy: After initialization, an otherwise valid A_Candidate changing by more than A_MaxRate shall latch A_RateTrip and shall not replace A_ProcessValue.
- **R5** **[safety-critical]**: Subsystem A shall satisfy: A_RateTrip or A_Enable FALSE shall force A_ValidOutput FALSE; A_Reset clears A_RateTrip only while disabled.
- **R6**: Subsystem A shall satisfy: At equality boundaries for A_MaxDifference and A_MaxRate, the A_Candidate remains acceptable.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: When both sensors are valid and agree within B_MaxDifference, B_Selected shall be their average.
- **R8** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: When both sensors are valid but B_Disagree beyond B_MaxDifference, B_Disagree shall be TRUE and B_Selected shall retain its previous value.
- **R9**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: When exactly one sensor is valid, B_Selected shall use that sensor and B_Degraded shall be TRUE.
- **R10** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: When neither sensor is valid, B_NoValidSensor shall be TRUE and B_Selected shall retain its previous value.
- **R11**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Degraded, B_Disagree, and B_NoValidSensor shall be mutually exclusive.
- **R12** **[safety-critical]**: A TRUE A_ValidOutput shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R13** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R14**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R15** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- Subsystem A: The function block is called exactly once per PLC scan.
- Subsystem A: Inputs are sampled at scan start and outputs are checked at scan end.
- Subsystem A: Each test starts from a fresh function-block instance.
- Subsystem B: B_MaxDifference is non-negative and constant during a test.
- Subsystem B: B_Selected initializes to 0.0 in a fresh instance.
- Subsystem B: Each test starts from a fresh function-block instance.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

# C07_B09_composite: Composed supervisory control: Clamped analog scaling with range status -> Redundant analog sensor selection

## Objective

Implement `C07_B09_composite` as an IEC-ST Core v1 function block in the Analog processing category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A_Raw below zero shall set A_UnderRange, clear A_OverRange, and clamp A_Engineering to 0.0.
- **R2**: Subsystem A shall satisfy: A_Raw above 4095 shall set A_OverRange, clear A_UnderRange, and clamp A_Engineering to 10.0.
- **R3**: Subsystem A shall satisfy: In-range A_Raw shall clear both flags and scale linearly to 0.0 through 10.0.
- **R4**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: When both sensors are valid and agree within B_MaxDifference, B_Selected shall be their average.
- **R5** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: When both sensors are valid but B_Disagree beyond B_MaxDifference, B_Disagree shall be TRUE and B_Selected shall retain its previous value.
- **R6**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: When exactly one sensor is valid, B_Selected shall use that sensor and B_Degraded shall be TRUE.
- **R7** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: When neither sensor is valid, B_NoValidSensor shall be TRUE and B_Selected shall retain its previous value.
- **R8**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Degraded, B_Disagree, and B_NoValidSensor shall be mutually exclusive.
- **R9** **[safety-critical]**: A TRUE A_UnderRange shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R10** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R11**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R12** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.
- MaxDifference is non-negative and constant during a test.
- Selected initializes to 0.0 in a fresh instance.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

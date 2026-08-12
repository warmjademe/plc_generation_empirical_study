# C07_B10_composite: Composed supervisory control: Clamped analog scaling with range status -> Rate-of-change monitoring with latched trip

## Objective

Implement `C07_B10_composite` as an IEC-ST Core v1 function block in the Analog processing category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A_Raw below zero shall set A_UnderRange, clear A_OverRange, and clamp A_Engineering to 0.0.
- **R2**: Subsystem A shall satisfy: A_Raw above 4095 shall set A_OverRange, clear A_UnderRange, and clamp A_Engineering to 10.0.
- **R3**: Subsystem A shall satisfy: In-range A_Raw shall clear both flags and scale linearly to 0.0 through 10.0.
- **R4**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: The first enabled sample shall initialize history, set B_Ready, and shall not B_Trip.
- **R5**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: For subsequent enabled samples, B_Delta shall equal B_Value minus the B_Previous enabled B_Value.
- **R6** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: A B_Delta above B_MaxRise or below negative B_MaxFall shall latch B_Trip.
- **R7** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Trip shall remain set until B_Reset occurs while B_Enable is FALSE.
- **R8**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Disabling monitoring shall clear B_Ready but shall not by itself clear B_Trip.
- **R9** **[safety-critical]**: A TRUE A_UnderRange shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R10** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R11**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R12** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

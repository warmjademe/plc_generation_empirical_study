# C03_B07_composite: Composed supervisory control: Safety-zone actuator arbitration -> Mutually exclusive heating and cooling with deadband

## Objective

Implement `C03_B07_composite` as an IEC-ST Core v1 function block in the Interlocks and safe outputs category. Preserve the supplied interface exactly.

## Requirements

- **R1** **[safety-critical]**: Subsystem A shall satisfy: Loss of A_GuardClosed or A_EStopOK shall disable all grants.
- **R2** **[safety-critical]**: Subsystem A shall satisfy: Authorized A_ManualRequest has highest priority.
- **R3**: Subsystem A shall satisfy: A_RobotRequest has priority over A_ConveyorRequest when manual mode is not granted.
- **R4** **[safety-critical]**: Subsystem A shall satisfy: At most one grant shall be TRUE.
- **R5**: Subsystem A shall satisfy: A_Conflict shall indicate more than one eligible request before arbitration.
- **R6**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Heat shall turn on below B_Setpoint minus 1.0 while enabled and safe.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Cool shall turn on above B_Setpoint plus 1.0 while enabled and safe.
- **R8**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Neither output shall be active inside the inclusive deadband.
- **R9** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Heat and B_Cool shall never be active together, and B_SafetyTrip shall turn both off.
- **R10** **[safety-critical]**: A TRUE A_RobotEnable shall latch CrossReady unless CrossReset is TRUE in the same scan.
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

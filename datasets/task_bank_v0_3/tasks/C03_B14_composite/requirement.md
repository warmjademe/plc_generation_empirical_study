# C03_B14_composite: Composed supervisory control: Mutually exclusive heating and cooling with deadband -> Safety-zone actuator arbitration

## Objective

Implement `C03_B14_composite` as an IEC-ST Core v1 function block in the Interlocks and safe outputs category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A_Heat shall turn on below A_Setpoint minus 1.0 while enabled and safe.
- **R2**: Subsystem A shall satisfy: A_Cool shall turn on above A_Setpoint plus 1.0 while enabled and safe.
- **R3**: Subsystem A shall satisfy: Neither output shall be active inside the inclusive deadband.
- **R4** **[safety-critical]**: Subsystem A shall satisfy: A_Heat and A_Cool shall never be active together, and A_SafetyTrip shall turn both off.
- **R5** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Loss of B_GuardClosed or B_EStopOK shall disable all grants.
- **R6** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Authorized B_ManualRequest has highest priority.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_RobotRequest has priority over B_ConveyorRequest when manual mode is not granted.
- **R8** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: At most one grant shall be TRUE.
- **R9**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Conflict shall indicate more than one eligible request before arbitration.
- **R10** **[safety-critical]**: A TRUE A_Heat shall latch CrossReady unless CrossReset is TRUE in the same scan.
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

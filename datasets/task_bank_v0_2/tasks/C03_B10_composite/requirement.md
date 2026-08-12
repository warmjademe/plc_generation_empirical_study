# C03_B10_composite: Composed supervisory control: Pump and discharge-valve interlock -> Safety-zone actuator arbitration

## Objective

Implement `C03_B10_composite` as an IEC-ST Core v1 function block in the Interlocks and safe outputs category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A_ValveCommand shall follow a valid A_RunRequest while A_TankLevelOK and not A_Stop hold.
- **R2** **[safety-critical]**: Subsystem A shall satisfy: A_PumpCommand requires A_ValveFeedbackOpen in addition to the valve-command permissives.
- **R3** **[safety-critical]**: Subsystem A shall satisfy: A_PumpCommand shall be FALSE when A_Stop or loss of A_TankLevelOK is active.
- **R4** **[safety-critical]**: Subsystem A shall satisfy: A_InterlockAlarm shall be TRUE when A_PumpFeedback is TRUE while valve feedback is closed.
- **R5** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Loss of B_GuardClosed or B_EStopOK shall disable all grants.
- **R6** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Authorized B_ManualRequest has highest priority.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_RobotRequest has priority over B_ConveyorRequest when manual mode is not granted.
- **R8** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: At most one grant shall be TRUE.
- **R9**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Conflict shall indicate more than one eligible request before arbitration.
- **R10** **[safety-critical]**: A TRUE A_ValveCommand shall latch CrossReady unless CrossReset is TRUE in the same scan.
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

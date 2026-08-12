# C03_B06_composite: Composed supervisory control: Safety-zone actuator arbitration -> Pump and discharge-valve interlock

## Objective

Implement `C03_B06_composite` as an IEC-ST Core v1 function block in the Interlocks and safe outputs category. Preserve the supplied interface exactly.

## Requirements

- **R1** **[safety-critical]**: Subsystem A shall satisfy: Loss of A_GuardClosed or A_EStopOK shall disable all grants.
- **R2** **[safety-critical]**: Subsystem A shall satisfy: Authorized A_ManualRequest has highest priority.
- **R3**: Subsystem A shall satisfy: A_RobotRequest has priority over A_ConveyorRequest when manual mode is not granted.
- **R4** **[safety-critical]**: Subsystem A shall satisfy: At most one grant shall be TRUE.
- **R5**: Subsystem A shall satisfy: A_Conflict shall indicate more than one eligible request before arbitration.
- **R6**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_ValveCommand shall follow a valid B_RunRequest while B_TankLevelOK and not B_Stop hold.
- **R7** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_PumpCommand requires B_ValveFeedbackOpen in addition to the valve-command permissives.
- **R8** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_PumpCommand shall be FALSE when B_Stop or loss of B_TankLevelOK is active.
- **R9** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_InterlockAlarm shall be TRUE when B_PumpFeedback is TRUE while valve feedback is closed.
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

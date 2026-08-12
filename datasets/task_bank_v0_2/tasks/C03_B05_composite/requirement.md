# C03_B05_composite: Composed supervisory control: Safety-zone actuator arbitration -> Three-conveyor downstream interlock

## Objective

Implement `C03_B05_composite` as an IEC-ST Core v1 function block in the Interlocks and safe outputs category. Preserve the supplied interface exactly.

## Requirements

- **R1** **[safety-critical]**: Subsystem A shall satisfy: Loss of A_GuardClosed or A_EStopOK shall disable all grants.
- **R2** **[safety-critical]**: Subsystem A shall satisfy: Authorized A_ManualRequest has highest priority.
- **R3**: Subsystem A shall satisfy: A_RobotRequest has priority over A_ConveyorRequest when manual mode is not granted.
- **R4** **[safety-critical]**: Subsystem A shall satisfy: At most one grant shall be TRUE.
- **R5**: Subsystem A shall satisfy: A_Conflict shall indicate more than one eligible request before arbitration.
- **R6** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_C3Run shall require B_RunRequest, B_C3Available, B_C3Clear, and not B_Stop.
- **R7** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_C2Run shall require B_C3Run, B_C2Available, and B_C2Clear.
- **R8** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_C1Run shall require B_C2Run and B_C1Clear.
- **R9** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Stop shall turn all three commands off.
- **R10**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Blocked shall indicate B_RunRequest with at least one unavailable or uncleared stage.
- **R11** **[safety-critical]**: A TRUE A_RobotEnable shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R12** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R13**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R14** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

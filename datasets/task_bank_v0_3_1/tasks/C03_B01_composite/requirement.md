# C03_B01_composite: Composed supervisory control: Three-conveyor downstream interlock -> Safety-zone actuator arbitration

## Objective

Implement `C03_B01_composite` as an IEC-ST Core v1 function block in the Interlocks and safe outputs category. Preserve the supplied interface exactly.

## Requirements

- **R1** **[safety-critical]**: Subsystem A shall satisfy: A_C3Run shall require A_RunRequest, A_C3Available, A_C3Clear, and not A_Stop.
- **R2** **[safety-critical]**: Subsystem A shall satisfy: A_C2Run shall require A_C3Run, A_C2Available, and A_C2Clear.
- **R3** **[safety-critical]**: Subsystem A shall satisfy: A_C1Run shall require A_C2Run and A_C1Clear.
- **R4** **[safety-critical]**: Subsystem A shall satisfy: A_Stop shall turn all three commands off.
- **R5**: Subsystem A shall satisfy: A_Blocked shall indicate A_RunRequest with at least one unavailable or uncleared stage.
- **R6** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Loss of B_GuardClosed or B_EStopOK shall disable all grants.
- **R7** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Authorized B_ManualRequest has highest priority.
- **R8**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_RobotRequest has priority over B_ConveyorRequest when manual mode is not granted.
- **R9** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: At most one grant shall be TRUE.
- **R10**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Conflict shall indicate more than one eligible request before arbitration.
- **R11** **[safety-critical]**: A TRUE A_C1Run shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R12** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R13**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R14** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

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

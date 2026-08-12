# C04_B09_composite: Composed supervisory control: Armed falling-edge pulse -> Qualified event capture with saturation

## Objective

Implement `C04_B09_composite` as an IEC-ST Core v1 function block in the Edge and event handling category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A_Armed shall equal A_Arm at the end of each scan.
- **R2**: Subsystem A shall satisfy: A_Pulse shall occur on a TRUE-to-FALSE A_Signal transition only when A_Arm is TRUE.
- **R3**: Subsystem A shall satisfy: Disarming shall suppress A_Pulse without corrupting future edge detection.
- **R4**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset shall clear B_Count and B_AcceptedPulse.
- **R5**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Only a rising B_Event edge with B_Qualify TRUE and B_Count below B_MaxCount shall increment B_Count.
- **R6** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Count shall not exceed B_MaxCount.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_AtLimit shall be TRUE exactly when B_Count is at least B_MaxCount.
- **R8** **[safety-critical]**: A TRUE A_Pulse shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R9** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R10**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R11** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.
- MaxCount is constant during a test and is at least 1.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

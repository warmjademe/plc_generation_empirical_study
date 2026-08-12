# C04_R15_lean_composite: Composed supervisory control: Armed falling-edge pulse -> Voted permissive with qualified bypass and diagnostics

## Objective

Implement `C04_R15_lean_composite` as an IEC-ST Core v1 function block in the Edge and event handling category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A_Armed shall equal A_Arm at the end of each scan.
- **R2**: Subsystem A shall satisfy: A_Pulse shall occur on a TRUE-to-FALSE A_Signal transition only when A_Arm is TRUE.
- **R3**: Subsystem A shall satisfy: Disarming shall suppress A_Pulse without corrupting future edge detection.
- **R4**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: The selected request shall be B_AutoRequest in automatic mode and B_ManualRequest otherwise.
- **R5** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Without bypass, B_RunPermit requires B_SafetyOK and at least two TRUE channels.
- **R6** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Bypass may latch only in manual mode when B_BypassRequest, B_BypassPermit, B_SafetyOK, and at least one channel are TRUE.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset may clear B_BypassActive only when neither automatic nor manual request is active.
- **R8**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Degraded shall identify a permitted run with channel disagreement or active bypass; B_Blocked shall identify a selected request without B_RunPermit.
- **R9** **[safety-critical]**: A TRUE A_Pulse shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R10** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R11**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R12** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

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

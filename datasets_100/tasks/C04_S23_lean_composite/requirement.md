# C04_S23_lean_composite: Composed supervisory control: Voted permissive with qualified bypass and diagnostics -> Armed falling-edge pulse

## Objective

Implement `C04_S23_lean_composite` as an IEC-ST Core v1 function block in the Boolean and conditional logic category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: The selected request shall be A_AutoRequest in automatic mode and A_ManualRequest otherwise.
- **R2** **[safety-critical]**: Subsystem A shall satisfy: Without bypass, A_RunPermit requires A_SafetyOK and at least two TRUE channels.
- **R3** **[safety-critical]**: Subsystem A shall satisfy: Bypass may latch only in manual mode when A_BypassRequest, A_BypassPermit, A_SafetyOK, and at least one channel are TRUE.
- **R4**: Subsystem A shall satisfy: A_Reset may clear A_BypassActive only when neither automatic nor manual request is active.
- **R5**: Subsystem A shall satisfy: A_Degraded shall identify a permitted run with channel disagreement or active bypass; A_Blocked shall identify a selected request without A_RunPermit.
- **R6**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Armed shall equal B_Arm at the end of each scan.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Pulse shall occur on a TRUE-to-FALSE B_Signal transition only when B_Arm is TRUE.
- **R8**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Disarming shall suppress B_Pulse without corrupting future edge detection.
- **R9** **[safety-critical]**: A TRUE A_RunPermit shall latch CrossReady unless CrossReset is TRUE in the same scan.
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

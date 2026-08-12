# C04_R17_lean_composite: Composed supervisory control: Mode-dependent command selection -> Dual-event priority capture with lockout

## Objective

Implement `C04_R17_lean_composite` as an IEC-ST Core v1 function block in the Boolean and conditional logic category. Preserve the supplied interface exactly.

## Requirements

- **R1** **[safety-critical]**: Subsystem A shall satisfy: A_Command shall follow A_AutoDemand in automatic mode and A_ManualDemand in manual mode, but only when A_SafetyOK is TRUE and A_Inhibit is FALSE.
- **R2**: Subsystem A shall satisfy: A_Blocked shall be TRUE when the selected request is TRUE but safety is not OK or A_Inhibit is TRUE.
- **R3**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset shall clear B_Captured, B_Code, and B_Pulse.
- **R4**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: While armed and not B_Captured, a rising B_EventA shall capture B_Code 1.
- **R5**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: A simultaneous rising edge shall select B_EventA over B_EventB.
- **R6**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: A rising B_EventB without B_EventA shall capture B_Code 2.
- **R7** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: After capture, later events shall not change B_Code until B_Reset.
- **R8** **[safety-critical]**: A TRUE A_Command shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R9** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R10**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R11** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

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

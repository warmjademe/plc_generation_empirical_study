# C02_B16_composite: Composed supervisory control: Local/remote command latch -> Mode-selected start latch with restart inhibit

## Objective

Implement `C02_B16_composite` as an IEC-ST Core v1 function block in the Start/stop and retained state category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A_SelectedStart shall use A_RemoteStart in remote mode and A_LocalStart in local mode.
- **R2** **[safety-critical]**: Subsystem A shall satisfy: A_Stop or loss of A_Permit shall force A_Running FALSE.
- **R3**: Subsystem A shall satisfy: The selected start shall latch A_Running only while A_Permit is TRUE and A_Stop is FALSE.
- **R4**: Subsystem A shall satisfy: A start from the non-selected mode shall have no effect.
- **R5**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_AutoMode shall select B_AutoStart; manual mode shall select B_ManualStart.
- **R6** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Stop, B_Enable FALSE, or B_SafetyOK FALSE shall force B_Running FALSE with priority over every start.
- **R7** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Safety loss while B_Running or while a start is requested shall latch B_RestartRequired.
- **R8**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_RestartRequired may clear only when B_Reset is TRUE, B_SafetyOK and B_Enable are TRUE, and the selected start is released.
- **R9** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: A start presented while B_RestartRequired is TRUE shall not run and shall pulse B_RejectedStart.
- **R10**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: With all permissions healthy and no restart inhibit, a selected start shall latch B_Running until a B_Stop condition occurs.
- **R11** **[safety-critical]**: A TRUE A_Running shall latch CrossReady unless CrossReset is TRUE in the same scan.
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

# C02_B17_composite: Composed supervisory control: Mode-selected start latch with restart inhibit -> Fault lockout with qualified manual reset

## Objective

Implement `C02_B17_composite` as an IEC-ST Core v1 function block in the Start/stop and retained state category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A_AutoMode shall select A_AutoStart; manual mode shall select A_ManualStart.
- **R2** **[safety-critical]**: Subsystem A shall satisfy: A_Stop, A_Enable FALSE, or A_SafetyOK FALSE shall force A_Running FALSE with priority over every start.
- **R3** **[safety-critical]**: Subsystem A shall satisfy: Safety loss while A_Running or while a start is requested shall latch A_RestartRequired.
- **R4**: Subsystem A shall satisfy: A_RestartRequired may clear only when A_Reset is TRUE, A_SafetyOK and A_Enable are TRUE, and the selected start is released.
- **R5** **[safety-critical]**: Subsystem A shall satisfy: A start presented while A_RestartRequired is TRUE shall not run and shall pulse A_RejectedStart.
- **R6**: Subsystem A shall satisfy: With all permissions healthy and no restart inhibit, a selected start shall latch A_Running until a A_Stop condition occurs.
- **R7** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Fault shall immediately B_Stop B_Running and latch B_LockedOut TRUE.
- **R8**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset shall clear B_LockedOut only when B_Fault is FALSE and B_Start is FALSE.
- **R9** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Start shall not run the equipment while B_LockedOut, B_Stop, or loss of B_Permit is active.
- **R10** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Clearing the lockout shall not automatically restart the equipment.
- **R11**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: A new B_Start after a successful B_Reset may latch B_Running TRUE.
- **R12** **[safety-critical]**: A TRUE A_Running shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R13** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R14**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R15** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

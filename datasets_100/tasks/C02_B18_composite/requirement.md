# C02_B18_composite: Composed supervisory control: Mode-selected start latch with restart inhibit -> Safe restart after power or safety interruption

## Objective

Implement `C02_B18_composite` as an IEC-ST Core v1 function block in the Start/stop and retained state category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A_AutoMode shall select A_AutoStart; manual mode shall select A_ManualStart.
- **R2** **[safety-critical]**: Subsystem A shall satisfy: A_Stop, A_Enable FALSE, or A_SafetyOK FALSE shall force A_Running FALSE with priority over every start.
- **R3** **[safety-critical]**: Subsystem A shall satisfy: Safety loss while A_Running or while a start is requested shall latch A_RestartRequired.
- **R4**: Subsystem A shall satisfy: A_RestartRequired may clear only when A_Reset is TRUE, A_SafetyOK and A_Enable are TRUE, and the selected start is released.
- **R5** **[safety-critical]**: Subsystem A shall satisfy: A start presented while A_RestartRequired is TRUE shall not run and shall pulse A_RejectedStart.
- **R6**: Subsystem A shall satisfy: With all permissions healthy and no restart inhibit, a selected start shall latch A_Running until a A_Stop condition occurs.
- **R7** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Loss of B_PowerOK or B_SafetyOK shall B_Stop B_Running and set B_RestartInhibit.
- **R8** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Stop shall B_Stop B_Running without by itself setting B_RestartInhibit.
- **R9**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset may clear B_RestartInhibit only when B_PowerOK and B_SafetyOK are TRUE and B_Start is FALSE.
- **R10** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Running shall remain FALSE while B_RestartInhibit is TRUE.
- **R11**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: After B_Reset, a new B_Start may run the machine when B_PowerOK, B_SafetyOK, and not B_Stop hold.
- **R12** **[safety-critical]**: A TRUE A_Running shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R13** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R14**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R15** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- Subsystem A: The function block is called exactly once per PLC scan.
- Subsystem A: Inputs are sampled at scan start and outputs are checked at scan end.
- Subsystem A: Each test starts from a fresh function-block instance.
- Subsystem B: The function block is called exactly once per PLC scan.
- Subsystem B: Inputs are sampled at scan B_Start and outputs are checked at scan end.
- Subsystem B: Each test starts from a fresh function-block instance.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

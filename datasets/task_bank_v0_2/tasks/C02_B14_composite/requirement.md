# C02_B14_composite: Composed supervisory control: Local/remote command latch -> Safe restart after power or safety interruption

## Objective

Implement `C02_B14_composite` as an IEC-ST Core v1 function block in the Start/stop and retained state category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A_SelectedStart shall use A_RemoteStart in remote mode and A_LocalStart in local mode.
- **R2** **[safety-critical]**: Subsystem A shall satisfy: A_Stop or loss of A_Permit shall force A_Running FALSE.
- **R3**: Subsystem A shall satisfy: The selected start shall latch A_Running only while A_Permit is TRUE and A_Stop is FALSE.
- **R4**: Subsystem A shall satisfy: A start from the non-selected mode shall have no effect.
- **R5** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Loss of B_PowerOK or B_SafetyOK shall B_Stop B_Running and set B_RestartInhibit.
- **R6** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Stop shall B_Stop B_Running without by itself setting B_RestartInhibit.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset may clear B_RestartInhibit only when B_PowerOK and B_SafetyOK are TRUE and B_Start is FALSE.
- **R8** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Running shall remain FALSE while B_RestartInhibit is TRUE.
- **R9**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: After B_Reset, a new B_Start may run the machine when B_PowerOK, B_SafetyOK, and not B_Stop hold.
- **R10** **[safety-critical]**: A TRUE A_Running shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R11** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R12**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R13** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

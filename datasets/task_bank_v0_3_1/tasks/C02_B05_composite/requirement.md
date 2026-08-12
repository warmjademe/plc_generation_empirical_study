# C02_B05_composite: Composed supervisory control: Safe restart after power or safety interruption -> Fault lockout with qualified manual reset

## Objective

Implement `C02_B05_composite` as an IEC-ST Core v1 function block in the Start/stop and retained state category. Preserve the supplied interface exactly.

## Requirements

- **R1** **[safety-critical]**: Subsystem A shall satisfy: Loss of A_PowerOK or A_SafetyOK shall A_Stop A_Running and set A_RestartInhibit.
- **R2** **[safety-critical]**: Subsystem A shall satisfy: A_Stop shall A_Stop A_Running without by itself setting A_RestartInhibit.
- **R3**: Subsystem A shall satisfy: A_Reset may clear A_RestartInhibit only when A_PowerOK and A_SafetyOK are TRUE and A_Start is FALSE.
- **R4** **[safety-critical]**: Subsystem A shall satisfy: A_Running shall remain FALSE while A_RestartInhibit is TRUE.
- **R5**: Subsystem A shall satisfy: After A_Reset, a new A_Start may run the machine when A_PowerOK, A_SafetyOK, and not A_Stop hold.
- **R6** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Fault shall immediately B_Stop B_Running and latch B_LockedOut TRUE.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset shall clear B_LockedOut only when B_Fault is FALSE and B_Start is FALSE.
- **R8** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Start shall not run the equipment while B_LockedOut, B_Stop, or loss of B_Permit is active.
- **R9** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Clearing the lockout shall not automatically restart the equipment.
- **R10**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: A new B_Start after a successful B_Reset may latch B_Running TRUE.
- **R11** **[safety-critical]**: A TRUE A_Running shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R12** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R13**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R14** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- Subsystem A: The function block is called exactly once per PLC scan.
- Subsystem A: Inputs are sampled at scan A_Start and outputs are checked at scan end.
- Subsystem A: Each test starts from a fresh function-block instance.
- Subsystem B: The function block is called exactly once per PLC scan.
- Subsystem B: Inputs are sampled at scan B_Start and outputs are checked at scan end.
- Subsystem B: Each test starts from a fresh function-block instance.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

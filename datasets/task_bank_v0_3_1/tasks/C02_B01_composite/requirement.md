# C02_B01_composite: Composed supervisory control: Fault lockout with qualified manual reset -> Safe restart after power or safety interruption

## Objective

Implement `C02_B01_composite` as an IEC-ST Core v1 function block in the Start/stop and retained state category. Preserve the supplied interface exactly.

## Requirements

- **R1** **[safety-critical]**: Subsystem A shall satisfy: A_Fault shall immediately A_Stop A_Running and latch A_LockedOut TRUE.
- **R2**: Subsystem A shall satisfy: A_Reset shall clear A_LockedOut only when A_Fault is FALSE and A_Start is FALSE.
- **R3** **[safety-critical]**: Subsystem A shall satisfy: A_Start shall not run the equipment while A_LockedOut, A_Stop, or loss of A_Permit is active.
- **R4** **[safety-critical]**: Subsystem A shall satisfy: Clearing the lockout shall not automatically restart the equipment.
- **R5**: Subsystem A shall satisfy: A new A_Start after a successful A_Reset may latch A_Running TRUE.
- **R6** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Loss of B_PowerOK or B_SafetyOK shall B_Stop B_Running and set B_RestartInhibit.
- **R7** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Stop shall B_Stop B_Running without by itself setting B_RestartInhibit.
- **R8**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset may clear B_RestartInhibit only when B_PowerOK and B_SafetyOK are TRUE and B_Start is FALSE.
- **R9** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Running shall remain FALSE while B_RestartInhibit is TRUE.
- **R10**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: After B_Reset, a new B_Start may run the machine when B_PowerOK, B_SafetyOK, and not B_Stop hold.
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

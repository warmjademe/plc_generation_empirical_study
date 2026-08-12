# C02_B09_composite: Composed supervisory control: Enabled start/stop with forced shutdown -> Fault lockout with qualified manual reset

## Objective

Implement `C02_B09_composite` as an IEC-ST Core v1 function block in the Start/stop and retained state category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A_Ready shall be TRUE when A_Enable is TRUE and A_Stop is FALSE.
- **R2** **[safety-critical]**: Subsystem A shall satisfy: Loss of A_Enable or assertion of A_Stop shall force A_Running FALSE.
- **R3**: Subsystem A shall satisfy: A_Start shall latch A_Running only while A_Ready is TRUE.
- **R4** **[safety-critical]**: Subsystem A shall satisfy: Re-enabling without a new A_Start shall not restart the controller.
- **R5** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Fault shall immediately B_Stop B_Running and latch B_LockedOut TRUE.
- **R6**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset shall clear B_LockedOut only when B_Fault is FALSE and B_Start is FALSE.
- **R7** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Start shall not run the equipment while B_LockedOut, B_Stop, or loss of B_Permit is active.
- **R8** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Clearing the lockout shall not automatically restart the equipment.
- **R9**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: A new B_Start after a successful B_Reset may latch B_Running TRUE.
- **R10** **[safety-critical]**: A TRUE A_Running shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R11** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R12**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R13** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

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

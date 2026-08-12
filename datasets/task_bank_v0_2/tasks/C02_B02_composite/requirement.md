# C02_B02_composite: Composed supervisory control: Fault lockout with qualified manual reset -> Enabled start/stop with forced shutdown

## Objective

Implement `C02_B02_composite` as an IEC-ST Core v1 function block in the Start/stop and retained state category. Preserve the supplied interface exactly.

## Requirements

- **R1** **[safety-critical]**: Subsystem A shall satisfy: A_Fault shall immediately A_Stop A_Running and latch A_LockedOut TRUE.
- **R2**: Subsystem A shall satisfy: A_Reset shall clear A_LockedOut only when A_Fault is FALSE and A_Start is FALSE.
- **R3** **[safety-critical]**: Subsystem A shall satisfy: A_Start shall not run the equipment while A_LockedOut, A_Stop, or loss of A_Permit is active.
- **R4** **[safety-critical]**: Subsystem A shall satisfy: Clearing the lockout shall not automatically restart the equipment.
- **R5**: Subsystem A shall satisfy: A new A_Start after a successful A_Reset may latch A_Running TRUE.
- **R6**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Ready shall be TRUE when B_Enable is TRUE and B_Stop is FALSE.
- **R7** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Loss of B_Enable or assertion of B_Stop shall force B_Running FALSE.
- **R8**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Start shall latch B_Running only while B_Ready is TRUE.
- **R9** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Re-enabling without a new B_Start shall not restart the controller.
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

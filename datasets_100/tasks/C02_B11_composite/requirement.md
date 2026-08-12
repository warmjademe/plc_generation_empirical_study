# C02_B11_composite: Composed supervisory control: Enabled start/stop with forced shutdown -> Local/remote command latch

## Objective

Implement `C02_B11_composite` as an IEC-ST Core v1 function block in the Start/stop and retained state category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A_Ready shall be TRUE when A_Enable is TRUE and A_Stop is FALSE.
- **R2** **[safety-critical]**: Subsystem A shall satisfy: Loss of A_Enable or assertion of A_Stop shall force A_Running FALSE.
- **R3**: Subsystem A shall satisfy: A_Start shall latch A_Running only while A_Ready is TRUE.
- **R4** **[safety-critical]**: Subsystem A shall satisfy: Re-enabling without a new A_Start shall not restart the controller.
- **R5**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_SelectedStart shall use B_RemoteStart in remote mode and B_LocalStart in local mode.
- **R6** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Stop or loss of B_Permit shall force B_Running FALSE.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: The selected start shall latch B_Running only while B_Permit is TRUE and B_Stop is FALSE.
- **R8**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: A start from the non-selected mode shall have no effect.
- **R9** **[safety-critical]**: A TRUE A_Running shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R10** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R11**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R12** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- Subsystem A: The function block is called exactly once per PLC scan.
- Subsystem A: Inputs are sampled at scan A_Start and outputs are checked at scan end.
- Subsystem A: Each test starts from a fresh function-block instance.
- Subsystem B: The function block is called exactly once per PLC scan.
- Subsystem B: Inputs are sampled at scan start and outputs are checked at scan end.
- Subsystem B: Each test starts from a fresh function-block instance.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

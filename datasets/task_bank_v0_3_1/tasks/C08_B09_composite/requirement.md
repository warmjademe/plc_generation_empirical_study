# C08_B09_composite: Composed supervisory control: Branching item sorter sequence -> Pause/resume sequence with abort recovery

## Objective

Implement `C08_B09_composite` as an IEC-ST Core v1 function block in the Sequential state machines category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A_ItemPresent in wait A_State shall enter inspection.
- **R2**: Subsystem A shall satisfy: Inspection shall branch to reject when A_RejectClass is TRUE and to accept otherwise.
- **R3**: Subsystem A shall satisfy: A_TransferDone in either transfer A_State shall return to wait.
- **R4** **[safety-critical]**: Subsystem A shall satisfy: A_Inspect, A_AcceptGate, and A_RejectGate shall be mutually exclusive and match A_State.
- **R5** **[safety-critical]**: Subsystem A shall satisfy: A_Reset shall return to wait and close both gates.
- **R6**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Start shall begin Step 1 only when idle and not B_Aborted.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Advance shall move Step 1 to Step 2 and Step 2 to done only while not B_Paused.
- **R8**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Pause shall suppress active step outputs without losing B_State; B_Resume clears B_Paused.
- **R9** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Abort shall return B_State to idle, suppress outputs, clear B_Paused, and latch B_Aborted.
- **R10**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset shall clear B_Aborted only while B_Start, B_Advance, B_Pause, B_Resume, and B_Abort are all FALSE.
- **R11** **[safety-critical]**: A TRUE A_Inspect shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R12** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R13**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R14** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

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

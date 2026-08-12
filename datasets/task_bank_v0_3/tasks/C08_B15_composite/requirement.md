# C08_B15_composite: Composed supervisory control: Fill-mix-drain sequence -> Branching item sorter sequence

## Objective

Implement `C08_B15_composite` as an IEC-ST Core v1 function block in the Sequential state machines category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A_Start in idle shall enter fill and open only A_FillValve.
- **R2**: Subsystem A shall satisfy: A_HighLevel shall transition fill to mix; A_MixDone transitions mix to drain.
- **R3**: Subsystem A shall satisfy: A_LowLevel in drain shall return to idle and pulse A_Complete for one scan.
- **R4** **[safety-critical]**: Subsystem A shall satisfy: A_FillValve, A_Mixer, and A_DrainValve shall be mutually exclusive and correspond to A_State.
- **R5** **[safety-critical]**: Subsystem A shall satisfy: A_Abort shall immediately return to idle, close all actuators, and suppress A_Complete.
- **R6**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_ItemPresent in wait B_State shall enter inspection.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Inspection shall branch to reject when B_RejectClass is TRUE and to accept otherwise.
- **R8**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_TransferDone in either transfer B_State shall return to wait.
- **R9** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Inspect, B_AcceptGate, and B_RejectGate shall be mutually exclusive and match B_State.
- **R10** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset shall return to wait and close both gates.
- **R11** **[safety-critical]**: A TRUE A_FillValve shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R12** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R13**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R14** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

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

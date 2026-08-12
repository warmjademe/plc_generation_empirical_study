# C08_B06_composite: Composed supervisory control: State sequence with per-stage timeout -> Branching item sorter sequence

## Objective

Implement `C08_B06_composite` as an IEC-ST Core v1 function block in the Sequential state machines category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A_Start in idle shall enter stage 1 and energize only A_Actuator1.
- **R2**: Subsystem A shall satisfy: A_Sensor1 shall transition stage 1 to stage 2; A_Sensor2 shall A_Complete stage 2 and return idle.
- **R3** **[safety-critical]**: Subsystem A shall satisfy: Either stage remaining incomplete for 500 ms shall latch A_Fault and return idle with both actuators off.
- **R4** **[safety-critical]**: Subsystem A shall satisfy: A_Stop shall return idle and turn both actuators off without clearing A_Fault.
- **R5**: Subsystem A shall satisfy: A_ResetFault clears A_Fault only while A_Stop is TRUE and A_Start is FALSE.
- **R6**: Subsystem A shall satisfy: A_Complete shall pulse only on the stage-2-to-idle completion transition.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_ItemPresent in wait B_State shall enter inspection.
- **R8**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Inspection shall branch to reject when B_RejectClass is TRUE and to accept otherwise.
- **R9**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_TransferDone in either transfer B_State shall return to wait.
- **R10** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Inspect, B_AcceptGate, and B_RejectGate shall be mutually exclusive and match B_State.
- **R11** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset shall return to wait and close both gates.
- **R12** **[safety-critical]**: A TRUE A_Actuator1 shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R13** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R14**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R15** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- Subsystem A: The runtime scan period is 100 ms.
- Subsystem A: Sensor completion is expected within 500 ms of entering each stage.
- Subsystem A: Each test starts from a fresh function-block instance.
- Subsystem B: The function block is called exactly once per PLC scan.
- Subsystem B: Inputs are sampled at scan start and outputs are checked at scan end.
- Subsystem B: Each test starts from a fresh function-block instance.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

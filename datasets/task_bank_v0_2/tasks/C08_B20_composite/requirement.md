# C08_B20_composite: Composed supervisory control: Paused three-stage sequence with abort and per-stage timeout -> Fill-mix-drain sequence

## Objective

Implement `C08_B20_composite` as an IEC-ST Core v1 function block in the Sequential state machines category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A_Start in idle shall enter stage 1; each matching Done input advances exactly one stage, and A_Stage3Done returns idle with a one-scan A_Complete pulse.
- **R2** **[safety-critical]**: Subsystem A shall satisfy: A_Pause shall retain A_State while forcing every actuator FALSE; Done inputs while A_Paused shall not advance.
- **R3** **[safety-critical]**: Subsystem A shall satisfy: The active stage shall time out after 500 ms of unpaused execution and latch A_Fault.
- **R4** **[safety-critical]**: Subsystem A shall satisfy: A_Abort shall immediately return idle, force safe outputs, and latch A_Fault.
- **R5**: Subsystem A shall satisfy: A_Reset clears A_Fault only in idle while A_Start, A_Abort, and every Done input are FALSE.
- **R6** **[safety-critical]**: Subsystem A shall satisfy: At most one actuator may be TRUE, and A_Complete shall never coincide with an actuator.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Start in idle shall enter fill and open only B_FillValve.
- **R8**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_HighLevel shall transition fill to mix; B_MixDone transitions mix to drain.
- **R9**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_LowLevel in drain shall return to idle and pulse B_Complete for one scan.
- **R10** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_FillValve, B_Mixer, and B_DrainValve shall be mutually exclusive and correspond to B_State.
- **R11** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Abort shall immediately return to idle, close all actuators, and suppress B_Complete.
- **R12** **[safety-critical]**: A TRUE A_Actuator1 shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R13** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R14**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R15** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- The runtime scan period is 100 ms.
- Pausing resets rather than accumulates the stage timeout.
- Each test starts from a fresh function-block instance.
- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

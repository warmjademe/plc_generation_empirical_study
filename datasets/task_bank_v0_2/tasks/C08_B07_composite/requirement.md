# C08_B07_composite: Composed supervisory control: State sequence with per-stage timeout -> Fill-mix-drain sequence

## Objective

Implement `C08_B07_composite` as an IEC-ST Core v1 function block in the Sequential state machines category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A_Start in idle shall enter stage 1 and energize only A_Actuator1.
- **R2**: Subsystem A shall satisfy: A_Sensor1 shall transition stage 1 to stage 2; A_Sensor2 shall A_Complete stage 2 and return idle.
- **R3** **[safety-critical]**: Subsystem A shall satisfy: Either stage remaining incomplete for 500 ms shall latch A_Fault and return idle with both actuators off.
- **R4** **[safety-critical]**: Subsystem A shall satisfy: A_Stop shall return idle and turn both actuators off without clearing A_Fault.
- **R5**: Subsystem A shall satisfy: A_ResetFault clears A_Fault only while A_Stop is TRUE and A_Start is FALSE.
- **R6**: Subsystem A shall satisfy: A_Complete shall pulse only on the stage-2-to-idle completion transition.
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
- Sensor completion is expected within 500 ms of entering each stage.
- Each test starts from a fresh function-block instance.
- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

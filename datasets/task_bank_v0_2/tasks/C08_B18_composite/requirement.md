# C08_B18_composite: Composed supervisory control: Paused three-stage sequence with abort and per-stage timeout -> State sequence with per-stage timeout

## Objective

Implement `C08_B18_composite` as an IEC-ST Core v1 function block in the Sequential state machines category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A_Start in idle shall enter stage 1; each matching Done input advances exactly one stage, and A_Stage3Done returns idle with a one-scan A_Complete pulse.
- **R2** **[safety-critical]**: Subsystem A shall satisfy: A_Pause shall retain A_State while forcing every actuator FALSE; Done inputs while A_Paused shall not advance.
- **R3** **[safety-critical]**: Subsystem A shall satisfy: The active stage shall time out after 500 ms of unpaused execution and latch A_Fault.
- **R4** **[safety-critical]**: Subsystem A shall satisfy: A_Abort shall immediately return idle, force safe outputs, and latch A_Fault.
- **R5**: Subsystem A shall satisfy: A_Reset clears A_Fault only in idle while A_Start, A_Abort, and every Done input are FALSE.
- **R6** **[safety-critical]**: Subsystem A shall satisfy: At most one actuator may be TRUE, and A_Complete shall never coincide with an actuator.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Start in idle shall enter stage 1 and energize only B_Actuator1.
- **R8**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Sensor1 shall transition stage 1 to stage 2; B_Sensor2 shall B_Complete stage 2 and return idle.
- **R9** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Either stage remaining incomplete for 500 ms shall latch B_Fault and return idle with both actuators off.
- **R10** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Stop shall return idle and turn both actuators off without clearing B_Fault.
- **R11**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_ResetFault clears B_Fault only while B_Stop is TRUE and B_Start is FALSE.
- **R12**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Complete shall pulse only on the stage-2-to-idle completion transition.
- **R13** **[safety-critical]**: A TRUE A_Actuator1 shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R14** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R15**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R16** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- The runtime scan period is 100 ms.
- Pausing resets rather than accumulates the stage timeout.
- Each test starts from a fresh function-block instance.
- Sensor completion is expected within 500 ms of entering each stage.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

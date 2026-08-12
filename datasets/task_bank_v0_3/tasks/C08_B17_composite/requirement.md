# C08_B17_composite: Composed supervisory control: Paused three-stage sequence with abort and per-stage timeout -> Pause/resume sequence with abort recovery

## Objective

Implement `C08_B17_composite` as an IEC-ST Core v1 function block in the Sequential state machines category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A_Start in idle shall enter stage 1; each matching Done input advances exactly one stage, and A_Stage3Done returns idle with a one-scan A_Complete pulse.
- **R2** **[safety-critical]**: Subsystem A shall satisfy: A_Pause shall retain A_State while forcing every actuator FALSE; Done inputs while A_Paused shall not advance.
- **R3** **[safety-critical]**: Subsystem A shall satisfy: The active stage shall time out after 500 ms of unpaused execution and latch A_Fault.
- **R4** **[safety-critical]**: Subsystem A shall satisfy: A_Abort shall immediately return idle, force safe outputs, and latch A_Fault.
- **R5**: Subsystem A shall satisfy: A_Reset clears A_Fault only in idle while A_Start, A_Abort, and every Done input are FALSE.
- **R6** **[safety-critical]**: Subsystem A shall satisfy: At most one actuator may be TRUE, and A_Complete shall never coincide with an actuator.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Start shall begin Step 1 only when idle and not B_Aborted.
- **R8**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Advance shall move Step 1 to Step 2 and Step 2 to done only while not B_Paused.
- **R9**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Pause shall suppress active step outputs without losing B_State; B_Resume clears B_Paused.
- **R10** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Abort shall return B_State to idle, suppress outputs, clear B_Paused, and latch B_Aborted.
- **R11**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset shall clear B_Aborted only while B_Start, B_Advance, B_Pause, B_Resume, and B_Abort are all FALSE.
- **R12** **[safety-critical]**: A TRUE A_Actuator1 shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R13** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R14**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R15** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- Subsystem A: The runtime scan period is 100 ms.
- Subsystem A: Pausing resets rather than accumulates the stage timeout.
- Subsystem A: Each test starts from a fresh function-block instance.
- Subsystem B: The function block is called exactly once per PLC scan.
- Subsystem B: Inputs are sampled at scan B_Start and outputs are checked at scan end.
- Subsystem B: Each test starts from a fresh function-block instance.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

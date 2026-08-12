# C05_B13_composite: Composed supervisory control: Heartbeat watchdog timeout -> Two-stage timed startup with safe abort

## Objective

Implement `C05_B13_composite` as an IEC-ST Core v1 function block in the Timers and timeouts category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: While monitoring, a A_Heartbeat shall restart the 400 ms A_Watchdog interval.
- **R2** **[safety-critical]**: Subsystem A shall satisfy: Absence of A_Heartbeat for at least 400 ms shall latch A_TimedOut TRUE.
- **R3**: Subsystem A shall satisfy: A_Reset shall clear A_TimedOut only while A_MonitorEnable is FALSE.
- **R4**: Subsystem A shall satisfy: A_Healthy shall equal A_MonitorEnable and not A_TimedOut.
- **R5**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Start with B_Permit shall command B_Stage1 immediately.
- **R6** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Stage2 shall not B_Start until B_Stage1Feedback has remained TRUE for at least 300 ms.
- **R7** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: If B_Stage1Feedback is absent for 600 ms after B_Stage1 starts, B_Fault shall latch and both stages shall B_Stop.
- **R8** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Stop or loss of B_Permit shall turn both stages off immediately.
- **R9**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Fault remains latched until B_Stop is TRUE while B_Start is FALSE.
- **R10** **[safety-critical]**: A TRUE A_TimedOut shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R11** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R12**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R13** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- The runtime scan period is 100 ms.
- Heartbeat is a pulse lasting no more than one scan.
- Each test starts from a fresh function-block instance.
- Permit changes are sampled at scan start.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

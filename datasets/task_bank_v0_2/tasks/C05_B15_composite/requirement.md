# C05_B15_composite: Composed supervisory control: Heartbeat watchdog timeout -> Off-delay ventilation fan

## Objective

Implement `C05_B15_composite` as an IEC-ST Core v1 function block in the Timers and timeouts category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: While monitoring, a A_Heartbeat shall restart the 400 ms A_Watchdog interval.
- **R2** **[safety-critical]**: Subsystem A shall satisfy: Absence of A_Heartbeat for at least 400 ms shall latch A_TimedOut TRUE.
- **R3**: Subsystem A shall satisfy: A_Reset shall clear A_TimedOut only while A_MonitorEnable is FALSE.
- **R4**: Subsystem A shall satisfy: A_Healthy shall equal A_MonitorEnable and not A_TimedOut.
- **R5**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Fan shall turn on without delay when B_Demand becomes TRUE and B_SafetyTrip is FALSE.
- **R6**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: After B_Demand becomes FALSE, B_Fan shall remain on for 300 ms unless B_SafetyTrip occurs.
- **R7** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_SafetyTrip shall turn B_Fan and B_RunOn off immediately.
- **R8**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_RunOn shall indicate the interval in which B_Demand is FALSE but the off-delay output remains TRUE.
- **R9** **[safety-critical]**: A TRUE A_TimedOut shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R10** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R11**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R12** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- The runtime scan period is 100 ms.
- Heartbeat is a pulse lasting no more than one scan.
- Each test starts from a fresh function-block instance.
- Demand is held TRUE for at least one scan before an off-delay test.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

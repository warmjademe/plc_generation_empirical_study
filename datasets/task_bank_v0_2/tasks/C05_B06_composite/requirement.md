# C05_B06_composite: Composed supervisory control: Star-delta motor transition -> Off-delay ventilation fan

## Objective

Implement `C05_B06_composite` as an IEC-ST Core v1 function block in the Timers and timeouts category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A_Start shall energize A_Main and A_Star when no A_Fault, A_Stop, or A_Overload is active.
- **R2** **[safety-critical]**: Subsystem A shall satisfy: After 500 ms in A_Star, A_Star shall turn off before A_Delta turns on after a 200 ms transition gap.
- **R3** **[safety-critical]**: Subsystem A shall satisfy: A_Star and A_Delta shall never be TRUE together.
- **R4** **[safety-critical]**: Subsystem A shall satisfy: A_Stop or A_Overload shall immediately turn off all contactors; A_Overload latches A_Fault.
- **R5**: Subsystem A shall satisfy: A_Reset clears A_Fault only while A_Start is FALSE and A_Overload is FALSE.
- **R6**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Fan shall turn on without delay when B_Demand becomes TRUE and B_SafetyTrip is FALSE.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: After B_Demand becomes FALSE, B_Fan shall remain on for 300 ms unless B_SafetyTrip occurs.
- **R8** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_SafetyTrip shall turn B_Fan and B_RunOn off immediately.
- **R9**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_RunOn shall indicate the interval in which B_Demand is FALSE but the off-delay output remains TRUE.
- **R10** **[safety-critical]**: A TRUE A_Main shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R11** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R12**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R13** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- The runtime scan period is 100 ms.
- Start may remain TRUE during normal operation.
- Each test starts from a fresh function-block instance.
- Demand is held TRUE for at least one scan before an off-delay test.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

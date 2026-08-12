# C05_B10_composite: Composed supervisory control: Off-delay ventilation fan -> Star-delta motor transition

## Objective

Implement `C05_B10_composite` as an IEC-ST Core v1 function block in the Timers and timeouts category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A_Fan shall turn on without delay when A_Demand becomes TRUE and A_SafetyTrip is FALSE.
- **R2**: Subsystem A shall satisfy: After A_Demand becomes FALSE, A_Fan shall remain on for 300 ms unless A_SafetyTrip occurs.
- **R3** **[safety-critical]**: Subsystem A shall satisfy: A_SafetyTrip shall turn A_Fan and A_RunOn off immediately.
- **R4**: Subsystem A shall satisfy: A_RunOn shall indicate the interval in which A_Demand is FALSE but the off-delay output remains TRUE.
- **R5**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Start shall energize B_Main and B_Star when no B_Fault, B_Stop, or B_Overload is active.
- **R6** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: After 500 ms in B_Star, B_Star shall turn off before B_Delta turns on after a 200 ms transition gap.
- **R7** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Star and B_Delta shall never be TRUE together.
- **R8** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Stop or B_Overload shall immediately turn off all contactors; B_Overload latches B_Fault.
- **R9**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset clears B_Fault only while B_Start is FALSE and B_Overload is FALSE.
- **R10** **[safety-critical]**: A TRUE A_Fan shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R11** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R12**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R13** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- The runtime scan period is 100 ms.
- Demand is held TRUE for at least one scan before an off-delay test.
- Each test starts from a fresh function-block instance.
- Start may remain TRUE during normal operation.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

# C05_B09_composite: Composed supervisory control: Off-delay ventilation fan -> Two-stage timed startup with safe abort

## Objective

Implement `C05_B09_composite` as an IEC-ST Core v1 function block in the Timers and timeouts category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A_Fan shall turn on without delay when A_Demand becomes TRUE and A_SafetyTrip is FALSE.
- **R2**: Subsystem A shall satisfy: After A_Demand becomes FALSE, A_Fan shall remain on for 300 ms unless A_SafetyTrip occurs.
- **R3** **[safety-critical]**: Subsystem A shall satisfy: A_SafetyTrip shall turn A_Fan and A_RunOn off immediately.
- **R4**: Subsystem A shall satisfy: A_RunOn shall indicate the interval in which A_Demand is FALSE but the off-delay output remains TRUE.
- **R5**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Start with B_Permit shall command B_Stage1 immediately.
- **R6** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Stage2 shall not B_Start until B_Stage1Feedback has remained TRUE for at least 300 ms.
- **R7** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: If B_Stage1Feedback is absent for 600 ms after B_Stage1 starts, B_Fault shall latch and both stages shall B_Stop.
- **R8** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Stop or loss of B_Permit shall turn both stages off immediately.
- **R9**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Fault remains latched until B_Stop is TRUE while B_Start is FALSE.
- **R10** **[safety-critical]**: A TRUE A_Fan shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R11** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R12**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R13** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- Subsystem A: The runtime scan period is 100 ms.
- Subsystem A: A_Demand is held TRUE for at least one scan before an off-delay test.
- Subsystem A: Each test starts from a fresh function-block instance.
- Subsystem B: The runtime scan period is 100 ms.
- Subsystem B: B_Permit changes are sampled at scan B_Start.
- Subsystem B: Each test starts from a fresh function-block instance.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

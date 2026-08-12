# C05_B01_composite: Composed supervisory control: Two-stage timed startup with safe abort -> Star-delta motor transition

## Objective

Implement `C05_B01_composite` as an IEC-ST Core v1 function block in the Timers and timeouts category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A_Start with A_Permit shall command A_Stage1 immediately.
- **R2** **[safety-critical]**: Subsystem A shall satisfy: A_Stage2 shall not A_Start until A_Stage1Feedback has remained TRUE for at least 300 ms.
- **R3** **[safety-critical]**: Subsystem A shall satisfy: If A_Stage1Feedback is absent for 600 ms after A_Stage1 starts, A_Fault shall latch and both stages shall A_Stop.
- **R4** **[safety-critical]**: Subsystem A shall satisfy: A_Stop or loss of A_Permit shall turn both stages off immediately.
- **R5**: Subsystem A shall satisfy: A_Fault remains latched until A_Stop is TRUE while A_Start is FALSE.
- **R6**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Start shall energize B_Main and B_Star when no B_Fault, B_Stop, or B_Overload is active.
- **R7** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: After 500 ms in B_Star, B_Star shall turn off before B_Delta turns on after a 200 ms transition gap.
- **R8** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Star and B_Delta shall never be TRUE together.
- **R9** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Stop or B_Overload shall immediately turn off all contactors; B_Overload latches B_Fault.
- **R10**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset clears B_Fault only while B_Start is FALSE and B_Overload is FALSE.
- **R11** **[safety-critical]**: A TRUE A_Stage1 shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R12** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R13**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R14** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- Subsystem A: The runtime scan period is 100 ms.
- Subsystem A: A_Permit changes are sampled at scan A_Start.
- Subsystem A: Each test starts from a fresh function-block instance.
- Subsystem B: The runtime scan period is 100 ms.
- Subsystem B: B_Start may remain TRUE during normal operation.
- Subsystem B: Each test starts from a fresh function-block instance.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

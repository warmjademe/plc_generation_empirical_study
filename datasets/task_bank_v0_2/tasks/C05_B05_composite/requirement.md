# C05_B05_composite: Composed supervisory control: Star-delta motor transition -> Two-stage timed startup with safe abort

## Objective

Implement `C05_B05_composite` as an IEC-ST Core v1 function block in the Timers and timeouts category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A_Start shall energize A_Main and A_Star when no A_Fault, A_Stop, or A_Overload is active.
- **R2** **[safety-critical]**: Subsystem A shall satisfy: After 500 ms in A_Star, A_Star shall turn off before A_Delta turns on after a 200 ms transition gap.
- **R3** **[safety-critical]**: Subsystem A shall satisfy: A_Star and A_Delta shall never be TRUE together.
- **R4** **[safety-critical]**: Subsystem A shall satisfy: A_Stop or A_Overload shall immediately turn off all contactors; A_Overload latches A_Fault.
- **R5**: Subsystem A shall satisfy: A_Reset clears A_Fault only while A_Start is FALSE and A_Overload is FALSE.
- **R6**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Start with B_Permit shall command B_Stage1 immediately.
- **R7** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Stage2 shall not B_Start until B_Stage1Feedback has remained TRUE for at least 300 ms.
- **R8** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: If B_Stage1Feedback is absent for 600 ms after B_Stage1 starts, B_Fault shall latch and both stages shall B_Stop.
- **R9** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Stop or loss of B_Permit shall turn both stages off immediately.
- **R10**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Fault remains latched until B_Stop is TRUE while B_Start is FALSE.
- **R11** **[safety-critical]**: A TRUE A_Main shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R12** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R13**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R14** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- The runtime scan period is 100 ms.
- Start may remain TRUE during normal operation.
- Each test starts from a fresh function-block instance.
- Permit changes are sampled at scan start.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

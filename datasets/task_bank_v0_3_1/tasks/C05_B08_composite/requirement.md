# C05_B08_composite: Composed supervisory control: Star-delta motor transition -> Pre-lube motor lifecycle with feedback fault and cooldown

## Objective

Implement `C05_B08_composite` as an IEC-ST Core v1 function block in the Timers and timeouts category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A_Start shall energize A_Main and A_Star when no A_Fault, A_Stop, or A_Overload is active.
- **R2** **[safety-critical]**: Subsystem A shall satisfy: After 500 ms in A_Star, A_Star shall turn off before A_Delta turns on after a 200 ms transition gap.
- **R3** **[safety-critical]**: Subsystem A shall satisfy: A_Star and A_Delta shall never be TRUE together.
- **R4** **[safety-critical]**: Subsystem A shall satisfy: A_Stop or A_Overload shall immediately turn off all contactors; A_Overload latches A_Fault.
- **R5**: Subsystem A shall satisfy: A_Reset clears A_Fault only while A_Start is FALSE and A_Overload is FALSE.
- **R6**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: A permitted B_Start shall enter pre-lube with B_LubePump TRUE and B_MotorCommand FALSE.
- **R7** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_MotorCommand may B_Start only after B_OilPressure remains TRUE for 300 ms.
- **R8** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Failure to receive B_MotorFeedback within 400 ms of B_MotorCommand shall latch B_Fault and enter B_Cooldown.
- **R9** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_OilPressure loss while running shall immediately B_Stop the motor, latch B_Fault, and enter B_Cooldown.
- **R10** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Stop or B_Permit loss shall B_Stop B_MotorCommand and enter a 300 ms B_Cooldown with B_LubePump remaining TRUE.
- **R11**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset clears B_Fault only in idle with B_Start FALSE; B_Cooldown completion returns idle without clearing B_Fault.
- **R12** **[safety-critical]**: A TRUE A_Main shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R13** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R14**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R15** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- Subsystem A: The runtime scan period is 100 ms.
- Subsystem A: A_Start may remain TRUE during normal operation.
- Subsystem A: Each test starts from a fresh function-block instance.
- Subsystem B: The runtime scan period is 100 ms.
- Subsystem B: B_Start may remain TRUE through startup.
- Subsystem B: Each test starts from a fresh function-block instance.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

# C05_B18_composite: Composed supervisory control: Pre-lube motor lifecycle with feedback fault and cooldown -> Star-delta motor transition

## Objective

Implement `C05_B18_composite` as an IEC-ST Core v1 function block in the Timers and timeouts category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A permitted A_Start shall enter pre-lube with A_LubePump TRUE and A_MotorCommand FALSE.
- **R2** **[safety-critical]**: Subsystem A shall satisfy: A_MotorCommand may A_Start only after A_OilPressure remains TRUE for 300 ms.
- **R3** **[safety-critical]**: Subsystem A shall satisfy: Failure to receive A_MotorFeedback within 400 ms of A_MotorCommand shall latch A_Fault and enter A_Cooldown.
- **R4** **[safety-critical]**: Subsystem A shall satisfy: A_OilPressure loss while running shall immediately A_Stop the motor, latch A_Fault, and enter A_Cooldown.
- **R5** **[safety-critical]**: Subsystem A shall satisfy: A_Stop or A_Permit loss shall A_Stop A_MotorCommand and enter a 300 ms A_Cooldown with A_LubePump remaining TRUE.
- **R6**: Subsystem A shall satisfy: A_Reset clears A_Fault only in idle with A_Start FALSE; A_Cooldown completion returns idle without clearing A_Fault.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Start shall energize B_Main and B_Star when no B_Fault, B_Stop, or B_Overload is active.
- **R8** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: After 500 ms in B_Star, B_Star shall turn off before B_Delta turns on after a 200 ms transition gap.
- **R9** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Star and B_Delta shall never be TRUE together.
- **R10** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Stop or B_Overload shall immediately turn off all contactors; B_Overload latches B_Fault.
- **R11**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset clears B_Fault only while B_Start is FALSE and B_Overload is FALSE.
- **R12** **[safety-critical]**: A TRUE A_LubePump shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R13** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R14**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R15** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- The runtime scan period is 100 ms.
- Start may remain TRUE through startup.
- Each test starts from a fresh function-block instance.
- Start may remain TRUE during normal operation.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

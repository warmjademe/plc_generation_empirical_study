# C05_B04_composite: Composed supervisory control: Two-stage timed startup with safe abort -> Pre-lube motor lifecycle with feedback fault and cooldown

## Objective

Implement `C05_B04_composite` as an IEC-ST Core v1 function block in the Timers and timeouts category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A_Start with A_Permit shall command A_Stage1 immediately.
- **R2** **[safety-critical]**: Subsystem A shall satisfy: A_Stage2 shall not A_Start until A_Stage1Feedback has remained TRUE for at least 300 ms.
- **R3** **[safety-critical]**: Subsystem A shall satisfy: If A_Stage1Feedback is absent for 600 ms after A_Stage1 starts, A_Fault shall latch and both stages shall A_Stop.
- **R4** **[safety-critical]**: Subsystem A shall satisfy: A_Stop or loss of A_Permit shall turn both stages off immediately.
- **R5**: Subsystem A shall satisfy: A_Fault remains latched until A_Stop is TRUE while A_Start is FALSE.
- **R6**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: A permitted B_Start shall enter pre-lube with B_LubePump TRUE and B_MotorCommand FALSE.
- **R7** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_MotorCommand may B_Start only after B_OilPressure remains TRUE for 300 ms.
- **R8** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Failure to receive B_MotorFeedback within 400 ms of B_MotorCommand shall latch B_Fault and enter B_Cooldown.
- **R9** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_OilPressure loss while running shall immediately B_Stop the motor, latch B_Fault, and enter B_Cooldown.
- **R10** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Stop or B_Permit loss shall B_Stop B_MotorCommand and enter a 300 ms B_Cooldown with B_LubePump remaining TRUE.
- **R11**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset clears B_Fault only in idle with B_Start FALSE; B_Cooldown completion returns idle without clearing B_Fault.
- **R12** **[safety-critical]**: A TRUE A_Stage1 shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R13** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R14**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R15** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- The runtime scan period is 100 ms.
- Permit changes are sampled at scan start.
- Each test starts from a fresh function-block instance.
- Start may remain TRUE through startup.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

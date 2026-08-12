# C05_B19_composite: Composed supervisory control: Pre-lube motor lifecycle with feedback fault and cooldown -> Off-delay ventilation fan

## Objective

Implement `C05_B19_composite` as an IEC-ST Core v1 function block in the Timers and timeouts category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A permitted A_Start shall enter pre-lube with A_LubePump TRUE and A_MotorCommand FALSE.
- **R2** **[safety-critical]**: Subsystem A shall satisfy: A_MotorCommand may A_Start only after A_OilPressure remains TRUE for 300 ms.
- **R3** **[safety-critical]**: Subsystem A shall satisfy: Failure to receive A_MotorFeedback within 400 ms of A_MotorCommand shall latch A_Fault and enter A_Cooldown.
- **R4** **[safety-critical]**: Subsystem A shall satisfy: A_OilPressure loss while running shall immediately A_Stop the motor, latch A_Fault, and enter A_Cooldown.
- **R5** **[safety-critical]**: Subsystem A shall satisfy: A_Stop or A_Permit loss shall A_Stop A_MotorCommand and enter a 300 ms A_Cooldown with A_LubePump remaining TRUE.
- **R6**: Subsystem A shall satisfy: A_Reset clears A_Fault only in idle with A_Start FALSE; A_Cooldown completion returns idle without clearing A_Fault.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Fan shall turn on without delay when B_Demand becomes TRUE and B_SafetyTrip is FALSE.
- **R8**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: After B_Demand becomes FALSE, B_Fan shall remain on for 300 ms unless B_SafetyTrip occurs.
- **R9** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_SafetyTrip shall turn B_Fan and B_RunOn off immediately.
- **R10**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_RunOn shall indicate the interval in which B_Demand is FALSE but the off-delay output remains TRUE.
- **R11** **[safety-critical]**: A TRUE A_LubePump shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R12** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R13**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R14** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- The runtime scan period is 100 ms.
- Start may remain TRUE through startup.
- Each test starts from a fresh function-block instance.
- Demand is held TRUE for at least one scan before an off-delay test.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

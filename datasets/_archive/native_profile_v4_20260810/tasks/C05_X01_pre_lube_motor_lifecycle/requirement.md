# C05_X01_pre_lube_motor_lifecycle: Pre-lube motor lifecycle with feedback fault and cooldown

## Objective

Implement `C05_X01_pre_lube_motor_lifecycle` as an IEC-ST Core v1 function block in the Timers and timeouts category. Preserve the supplied interface exactly.

## Requirements

- **R1**: A permitted start shall enter pre-lube with LubePump TRUE and MotorCommand FALSE.
- **R2** **[safety-critical]**: MotorCommand may start only after OilPressure remains TRUE for 300 ms.
- **R3** **[safety-critical]**: Failure to receive MotorFeedback within 400 ms of MotorCommand shall latch Fault and enter cooldown.
- **R4** **[safety-critical]**: OilPressure loss while running shall immediately stop the motor, latch Fault, and enter cooldown.
- **R5** **[safety-critical]**: Stop or Permit loss shall stop MotorCommand and enter a 300 ms cooldown with LubePump remaining TRUE.
- **R6**: Reset clears Fault only in idle with Start FALSE; cooldown completion returns idle without clearing Fault.

## Assumptions

- The runtime scan period is 100 ms.
- Start may remain TRUE through startup.
- Each test starts from a fresh function-block instance.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

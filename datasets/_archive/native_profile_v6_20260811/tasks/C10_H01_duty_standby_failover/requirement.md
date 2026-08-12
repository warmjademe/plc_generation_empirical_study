# C10_H01_duty_standby_failover: Duty-standby pump feedback failover

## Objective

Implement `C10_H01_duty_standby_failover` as an IEC-ST Core v1 function block in the Multi-device coordination category. Preserve the supplied interface exactly.

## Requirements

- **R1**: A new Demand shall command the available duty pump, or the standby if the duty pump is unavailable.
- **R2**: If the commanded pump lacks feedback for 300 ms, control shall transfer to an available standby pump.
- **R3** **[safety-critical]**: Both run commands shall never be TRUE simultaneously.
- **R4** **[safety-critical]**: Failure shall latch if demand cannot be served by an available pump with feedback after failover.
- **R5**: Demand FALSE shall stop both pumps; Reset may clear Failure only with Demand FALSE.

## Assumptions

- The runtime scan period is 100 ms.
- Pump feedback is sampled at scan start.
- Each test starts from a fresh function-block instance.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

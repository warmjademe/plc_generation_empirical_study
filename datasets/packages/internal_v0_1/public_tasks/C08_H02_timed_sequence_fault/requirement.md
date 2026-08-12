# C08_H02_timed_sequence_fault: State sequence with per-stage timeout

## Objective

Implement `C08_H02_timed_sequence_fault` as an IEC-ST Core v1 function block in the Sequential state machines category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Start in idle shall enter stage 1 and energize only Actuator1.
- **R2**: Sensor1 shall transition stage 1 to stage 2; Sensor2 shall complete stage 2 and return idle.
- **R3** **[safety-critical]**: Either stage remaining incomplete for 500 ms shall latch Fault and return idle with both actuators off.
- **R4** **[safety-critical]**: Stop shall return idle and turn both actuators off without clearing Fault.
- **R5**: ResetFault clears Fault only while Stop is TRUE and Start is FALSE.
- **R6**: Complete shall pulse only on the stage-2-to-idle completion transition.

## Assumptions

- The runtime scan period is 100 ms.
- Sensor completion is expected within 500 ms of entering each stage.
- Each test starts from a fresh function-block instance.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

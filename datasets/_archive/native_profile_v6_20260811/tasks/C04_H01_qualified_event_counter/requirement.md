# C04_H01_qualified_event_counter: Qualified event capture with saturation

## Objective

Implement `C04_H01_qualified_event_counter` as an IEC-ST Core v1 function block in the Edge and event handling category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Reset shall clear Count and AcceptedPulse.
- **R2**: Only a rising Event edge with Qualify TRUE and Count below MaxCount shall increment Count.
- **R3** **[safety-critical]**: Count shall not exceed MaxCount.
- **R4**: AtLimit shall be TRUE exactly when Count is at least MaxCount.

## Assumptions

- MaxCount is constant during a test and is at least 1.
- The function block is called exactly once per PLC scan.
- Each test starts from a fresh function-block instance.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

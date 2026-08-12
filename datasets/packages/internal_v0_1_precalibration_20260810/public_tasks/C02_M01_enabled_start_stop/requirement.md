# C02_M01_enabled_start_stop: Enabled start/stop with forced shutdown

## Objective

Implement `C02_M01_enabled_start_stop` as an IEC-ST Core v1 function block in the Start/stop and retained state category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Ready shall be TRUE when Enable is TRUE and Stop is FALSE.
- **R2** **[safety-critical]**: Loss of Enable or assertion of Stop shall force Running FALSE.
- **R3**: Start shall latch Running only while Ready is TRUE.
- **R4** **[safety-critical]**: Re-enabling without a new Start shall not restart the controller.

## Assumptions

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

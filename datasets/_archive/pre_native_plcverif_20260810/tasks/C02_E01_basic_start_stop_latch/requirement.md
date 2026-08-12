# C02_E01_basic_start_stop_latch: Stop-priority start/stop latch

## Objective

Implement `C02_E01_basic_start_stop_latch` as an IEC-ST Core v1 function block in the Start/stop and retained state category. Preserve the supplied interface exactly.

## Requirements

- **R1**: A Start command shall latch Running TRUE when Stop is FALSE.
- **R2** **[safety-critical]**: Stop shall force Running FALSE and shall have priority when Start and Stop are simultaneous.
- **R3**: Running shall retain its previous value when neither Start nor Stop is active.

## Assumptions

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

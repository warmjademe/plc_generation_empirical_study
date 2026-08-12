# C02_M02_local_remote_latch: Local/remote command latch

## Objective

Implement `C02_M02_local_remote_latch` as an IEC-ST Core v1 function block in the Start/stop and retained state category. Preserve the supplied interface exactly.

## Requirements

- **R1**: SelectedStart shall use RemoteStart in remote mode and LocalStart in local mode.
- **R2** **[safety-critical]**: Stop or loss of Permit shall force Running FALSE.
- **R3**: The selected start shall latch Running only while Permit is TRUE and Stop is FALSE.
- **R4**: A start from the non-selected mode shall have no effect.

## Assumptions

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

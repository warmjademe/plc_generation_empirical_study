# C10_E01_master_follower_coordination: Master-follower motor coordination

## Objective

Implement `C10_E01_master_follower_coordination` as an IEC-ST Core v1 function block in the Multi-device coordination category. Preserve the supplied interface exactly.

## Requirements

- **R1**: MasterRun shall be TRUE exactly when RunRequest and MasterReady are TRUE.
- **R2** **[safety-critical]**: FollowerRun shall require RunRequest, MasterRun, and FollowerReady.

## Assumptions

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

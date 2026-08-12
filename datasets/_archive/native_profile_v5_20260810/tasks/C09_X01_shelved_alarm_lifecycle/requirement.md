# C09_X01_shelved_alarm_lifecycle: Delayed warning, immediate trip, shelving, acknowledgement, and reset

## Objective

Implement `C09_X01_shelved_alarm_lifecycle` as an IEC-ST Core v1 function block in the Alarms and fault recovery category. Preserve the supplied interface exactly.

## Requirements

- **R1**: An enabled WarningCondition shall become Warning after 300 ms unless shelved or a trip is active.
- **R2** **[safety-critical]**: Shelve may suppress only warnings; TripCondition shall latch Trip and LockedOut immediately regardless of Shelve.
- **R3**: Every newly displayed Warning or Trip shall set Unacked; Acknowledge clears Unacked without clearing active alarms.
- **R4** **[safety-critical]**: Shelved follows Shelve only while no trip is active; a trip cancels Shelved.
- **R5**: Enable FALSE shall suppress Warning but shall not clear Trip or LockedOut.
- **R6** **[safety-critical]**: Reset clears Trip and LockedOut only when disabled and both conditions are FALSE.

## Assumptions

- The runtime scan period is 100 ms.
- Acknowledge may be held for more than one scan.
- Each test starts from a fresh function-block instance.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

# C09_H02_delayed_warning_trip_lockout: Delayed warning with trip lockout and acknowledgement

## Objective

Implement `C09_H02_delayed_warning_trip_lockout` as an IEC-ST Core v1 function block in the Alarms and fault recovery category. Preserve the supplied interface exactly.

## Requirements

- **R1**: WarningCondition shall assert Warning only after it remains enabled for 300 ms.
- **R2** **[safety-critical]**: TripCondition while enabled shall immediately latch Trip and LockedOut.
- **R3**: A newly asserted Warning or Trip shall set Unacked.
- **R4**: Acknowledge shall clear Unacked without clearing active Warning or latched Trip.
- **R5**: Reset shall clear Trip and LockedOut only while both conditions and Enable are FALSE.
- **R6** **[safety-critical]**: Disabling the system shall clear the non-latched Warning but not an existing Trip.

## Assumptions

- The runtime scan period is 100 ms.
- Acknowledge has priority over a new Unacked indication within the same scan.
- Each test starts from a fresh function-block instance.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

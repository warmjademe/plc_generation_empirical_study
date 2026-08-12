FUNCTION_BLOCK C06_E01_three_part_counter
VAR_INPUT
    PartPulse : BOOL;
    Reset : BOOL;
END_VAR
VAR_OUTPUT
    Count : INT;
    Complete : BOOL;
END_VAR
VAR
    PrevPart : BOOL := FALSE;
END_VAR

IF Reset THEN
    Count := 0;
ELSIF PartPulse OR (NOT PrevPart) AND (Count < 3) THEN
    Count := Count + 1;
END_IF;
Complete := Count = 3;
PrevPart := PartPulse;

END_FUNCTION_BLOCK

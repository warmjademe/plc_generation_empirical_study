FUNCTION_BLOCK C10_H02_fair_resource_arbiter
VAR_INPUT
    RequestA : BOOL;
    RequestB : BOOL;
    Done : BOOL;
    Emergency : BOOL;
    Reset : BOOL;
END_VAR
VAR_OUTPUT
    GrantA : BOOL;
    GrantB : BOOL;
    Busy : BOOL;
    Turn : INT;
    LockedOut : BOOL;
END_VAR

IF (Turn <> 1) AND (Turn <> 2) THEN Turn := 1; END_IF;
IF Emergency THEN
    GrantA := FALSE; GrantB := FALSE; Busy := FALSE; LockedOut := FALSE;
ELSE
    IF Reset AND (NOT RequestA) AND (NOT RequestB) THEN
        LockedOut := FALSE;
    END_IF;
    IF NOT LockedOut THEN
        IF Done THEN
            IF Busy THEN
                IF GrantA THEN Turn := 2; ELSE Turn := 1; END_IF;
            END_IF;
            GrantA := FALSE; GrantB := FALSE; Busy := FALSE;
        ELSIF NOT Busy THEN
            IF RequestA AND RequestB THEN
                IF Turn = 1 THEN GrantA := TRUE; ELSE GrantB := TRUE; END_IF;
                Busy := TRUE;
            ELSIF RequestA THEN
                GrantA := TRUE; GrantB := FALSE; Busy := TRUE;
            ELSIF RequestB THEN
                GrantA := FALSE; GrantB := TRUE; Busy := TRUE;
            END_IF;
        END_IF;
    END_IF;
END_IF;

END_FUNCTION_BLOCK

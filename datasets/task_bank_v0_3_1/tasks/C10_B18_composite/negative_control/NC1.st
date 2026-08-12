FUNCTION_BLOCK C10_B18_composite
VAR_INPUT
    A_LowDemand : BOOL;
    A_HighDemand : BOOL;
    A_Lead : INT;
    A_Available1 : BOOL;
    A_Available2 : BOOL;
    A_Available3 : BOOL;
    A_Feedback1 : BOOL;
    A_Feedback2 : BOOL;
    A_Feedback3 : BOOL;
    A_Stop : BOOL;
    A_Reset : BOOL;
    B_RequestA : BOOL;
    B_RequestB : BOOL;
    B_Done : BOOL;
    B_Emergency : BOOL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Run1 : BOOL;
    A_Run2 : BOOL;
    A_Run3 : BOOL;
    A_ActiveCount : INT;
    A_Failover : BOOL;
    A_Fault : BOOL;
    B_GrantA : BOOL;
    B_GrantB : BOOL;
    B_Busy : BOOL;
    B_Turn : INT;
    B_LockedOut : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_NoFeedback1 : TON;
    A_NoFeedback2 : TON;
    A_NoFeedback3 : TON;
    A_Failed1 : BOOL;
    A_Failed2 : BOOL;
    A_Failed3 : BOOL;
    A_Valid1 : BOOL;
    A_Valid2 : BOOL;
    A_Valid3 : BOOL;
    A_RequiredCount : INT;
END_VAR

A_NoFeedback1(IN := A_Run1 AND (NOT A_Feedback1), PT := T#300ms);
A_NoFeedback2(IN := A_Run2 AND (NOT A_Feedback2), PT := T#300ms);
A_NoFeedback3(IN := A_Run3 AND (NOT A_Feedback3), PT := T#300ms);
IF A_NoFeedback1.Q THEN A_Failed1 := TRUE; END_IF;
IF A_NoFeedback2.Q THEN A_Failed2 := TRUE; END_IF;
IF A_NoFeedback3.Q THEN A_Failed3 := TRUE; END_IF;
IF A_Reset AND (NOT A_LowDemand) AND (NOT A_HighDemand) AND (NOT A_Stop) THEN
    A_Failed1 := FALSE; A_Failed2 := FALSE; A_Failed3 := FALSE; A_Fault := FALSE;
END_IF;
A_Run1 := FALSE; A_Run2 := FALSE; A_Run3 := FALSE;
A_RequiredCount := 0;
IF A_HighDemand THEN A_RequiredCount := 2;
ELSIF A_LowDemand THEN A_RequiredCount := 1;
END_IF;
A_Valid1 := A_Available1 AND (NOT A_Failed1);
A_Valid2 := A_Available2 AND (NOT A_Failed2);
A_Valid3 := A_Available3 AND (NOT A_Failed3);
IF (NOT A_Stop) AND (A_RequiredCount > 0) THEN
    IF A_Lead = 2 THEN
        IF A_Valid2 THEN A_Run2 := TRUE;
        ELSIF A_Valid3 THEN A_Run3 := TRUE;
        ELSIF A_Valid1 THEN A_Run1 := TRUE;
        END_IF;
        IF A_RequiredCount = 2 THEN
            IF A_Valid3 AND (NOT A_Run3) THEN A_Run3 := TRUE;
            ELSIF A_Valid1 AND (NOT A_Run1) THEN A_Run1 := TRUE;
            ELSIF A_Valid2 AND (NOT A_Run2) THEN A_Run2 := TRUE;
            END_IF;
        END_IF;
    ELSIF A_Lead = 3 THEN
        IF A_Valid3 THEN A_Run3 := TRUE;
        ELSIF A_Valid1 THEN A_Run1 := TRUE;
        ELSIF A_Valid2 THEN A_Run2 := TRUE;
        END_IF;
        IF A_RequiredCount = 2 THEN
            IF A_Valid1 AND (NOT A_Run1) THEN A_Run1 := TRUE;
            ELSIF A_Valid2 AND (NOT A_Run2) THEN A_Run2 := TRUE;
            ELSIF A_Valid3 AND (NOT A_Run3) THEN A_Run3 := TRUE;
            END_IF;
        END_IF;
    ELSE
        IF A_Valid1 THEN A_Run1 := TRUE;
        ELSIF A_Valid2 THEN A_Run2 := TRUE;
        ELSIF A_Valid3 THEN A_Run3 := TRUE;
        END_IF;
        IF A_RequiredCount = 2 THEN
            IF A_Valid2 AND (NOT A_Run2) THEN A_Run2 := TRUE;
            ELSIF A_Valid3 AND (NOT A_Run3) THEN A_Run3 := TRUE;
            ELSIF A_Valid1 AND (NOT A_Run1) THEN A_Run1 := TRUE;
            END_IF;
        END_IF;
    END_IF;
END_IF;
A_ActiveCount := 0;
IF A_Run1 THEN A_ActiveCount := A_ActiveCount + 1; END_IF;
IF A_Run2 THEN A_ActiveCount := A_ActiveCount + 1; END_IF;
IF A_Run3 THEN A_ActiveCount := A_ActiveCount + 1; END_IF;
A_Failover := (A_RequiredCount > 0) AND ((A_ActiveCount < A_RequiredCount) OR ((A_Lead = 1) AND (NOT A_Run1)) OR ((A_Lead = 2) AND (NOT A_Run2)) OR ((A_Lead = 3) AND (NOT A_Run3)));
IF A_ActiveCount < A_RequiredCount THEN A_Fault := TRUE; END_IF;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_Run2 THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := FALSE;

IF SubsystemBEnable AND CrossReady THEN
    IF (B_Turn <> 1) AND (B_Turn <> 2) THEN B_Turn := 1; END_IF;
    IF B_Emergency THEN
        B_GrantA := FALSE; B_GrantB := FALSE; B_Busy := FALSE; B_LockedOut := TRUE;
    ELSE
        IF B_Reset AND (NOT B_RequestA) AND (NOT B_RequestB) THEN
            B_LockedOut := FALSE;
        END_IF;
        IF NOT B_LockedOut THEN
            IF B_Done THEN
                IF B_Busy THEN
                    IF B_GrantA THEN B_Turn := 2; ELSE B_Turn := 1; END_IF;
                END_IF;
                B_GrantA := FALSE; B_GrantB := FALSE; B_Busy := FALSE;
            ELSIF NOT B_Busy THEN
                IF B_RequestA AND B_RequestB THEN
                    IF B_Turn = 1 THEN B_GrantA := TRUE; ELSE B_GrantB := TRUE; END_IF;
                    B_Busy := TRUE;
                ELSIF B_RequestA THEN
                    B_GrantA := TRUE; B_GrantB := FALSE; B_Busy := TRUE;
                ELSIF B_RequestB THEN
                    B_GrantA := FALSE; B_GrantB := TRUE; B_Busy := TRUE;
                END_IF;
            END_IF;
        END_IF;
    END_IF;
ELSE
    B_GrantA := FALSE;
    B_GrantB := FALSE;
    B_Busy := FALSE;
    B_Turn := 0;
    B_LockedOut := FALSE;
END_IF;

END_FUNCTION_BLOCK

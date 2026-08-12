FUNCTION_BLOCK C10_B01_composite
VAR_INPUT
    A_Demand : BOOL;
    A_DutyIsPump1 : BOOL;
    A_Pump1Available : BOOL;
    A_Pump2Available : BOOL;
    A_Pump1Feedback : BOOL;
    A_Pump2Feedback : BOOL;
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
    A_Pump1Run : BOOL;
    A_Pump2Run : BOOL;
    A_FailoverActive : BOOL;
    A_Failure : BOOL;
    B_GrantA : BOOL;
    B_GrantB : BOOL;
    B_Busy : BOOL;
    B_Turn : INT;
    B_LockedOut : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_PrevDemand : BOOL;
    A_DutyNoFeedback : TON;
    A_StandbyNoFeedback : TON;
END_VAR

A_DutyNoFeedback(IN := A_Demand AND (NOT A_FailoverActive) AND ((A_Pump1Run AND (NOT A_Pump1Feedback)) OR (A_Pump2Run AND (NOT A_Pump2Feedback))), PT := T#300ms);
A_StandbyNoFeedback(IN := A_Demand AND A_FailoverActive AND ((A_Pump1Run AND (NOT A_Pump1Feedback)) OR (A_Pump2Run AND (NOT A_Pump2Feedback))), PT := T#300ms);
IF NOT A_Demand THEN
    A_Pump1Run := FALSE;
    A_Pump2Run := FALSE;
    A_FailoverActive := FALSE;
    IF A_Reset THEN A_Failure := FALSE; END_IF;
ELSIF NOT A_PrevDemand THEN
    IF A_DutyIsPump1 AND A_Pump1Available THEN
        A_Pump1Run := FALSE; A_Pump2Run := FALSE;
    ELSIF (NOT A_DutyIsPump1) AND A_Pump2Available THEN
        A_Pump1Run := FALSE; A_Pump2Run := TRUE;
    ELSIF A_Pump1Available THEN
        A_Pump1Run := TRUE; A_Pump2Run := FALSE; A_FailoverActive := TRUE;
    ELSIF A_Pump2Available THEN
        A_Pump1Run := FALSE; A_Pump2Run := TRUE; A_FailoverActive := TRUE;
    ELSE
        A_Failure := TRUE;
    END_IF;
ELSIF A_DutyNoFeedback.Q THEN
    IF A_Pump1Run AND A_Pump2Available AND (NOT A_FailoverActive) THEN
        A_Pump1Run := FALSE; A_Pump2Run := TRUE; A_FailoverActive := TRUE;
    ELSIF A_Pump2Run AND A_Pump1Available AND (NOT A_FailoverActive) THEN
        A_Pump1Run := TRUE; A_Pump2Run := FALSE; A_FailoverActive := TRUE;
    ELSE
        A_Pump1Run := FALSE; A_Pump2Run := FALSE; A_Failure := TRUE;
    END_IF;
ELSIF A_StandbyNoFeedback.Q THEN
    A_Pump1Run := FALSE; A_Pump2Run := FALSE; A_Failure := TRUE;
END_IF;
A_PrevDemand := A_Demand;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_Pump1Run THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := SubsystemBEnable AND (NOT CrossReady);

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

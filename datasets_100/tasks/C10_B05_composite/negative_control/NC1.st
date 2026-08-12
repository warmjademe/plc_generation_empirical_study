FUNCTION_BLOCK C10_B05_composite
VAR_INPUT
    A_RequestA : BOOL;
    A_RequestB : BOOL;
    A_Done : BOOL;
    A_Emergency : BOOL;
    A_Reset : BOOL;
    B_Demand : BOOL;
    B_DutyIsPump1 : BOOL;
    B_Pump1Available : BOOL;
    B_Pump2Available : BOOL;
    B_Pump1Feedback : BOOL;
    B_Pump2Feedback : BOOL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_GrantA : BOOL;
    A_GrantB : BOOL;
    A_Busy : BOOL;
    A_Turn : INT;
    A_LockedOut : BOOL;
    B_Pump1Run : BOOL;
    B_Pump2Run : BOOL;
    B_FailoverActive : BOOL;
    B_Failure : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    B_PrevDemand : BOOL;
    B_DutyNoFeedback : TON;
    B_StandbyNoFeedback : TON;
END_VAR

IF (A_Turn <> 1) AND (A_Turn <> 2) THEN A_Turn := 1; END_IF;
IF A_Emergency THEN
    A_GrantA := FALSE; A_GrantB := FALSE; A_Busy := FALSE; A_LockedOut := TRUE;
ELSE
    IF A_Reset AND (NOT A_RequestA) AND (NOT A_RequestB) THEN
        A_LockedOut := FALSE;
    END_IF;
    IF NOT A_LockedOut THEN
        IF A_Done THEN
            IF A_Busy THEN
                IF A_GrantA THEN A_Turn := 2; ELSE A_Turn := 1; END_IF;
            END_IF;
            A_GrantA := FALSE; A_GrantB := FALSE; A_Busy := FALSE;
        ELSIF NOT A_Busy THEN
            IF A_RequestA AND A_RequestB THEN
                IF A_Turn = 1 THEN A_GrantA := TRUE; ELSE A_GrantB := TRUE; END_IF;
                A_Busy := TRUE;
            ELSIF A_RequestA THEN
                A_GrantA := TRUE; A_GrantB := FALSE; A_Busy := TRUE;
            ELSIF A_RequestB THEN
                A_GrantA := FALSE; A_GrantB := TRUE; A_Busy := TRUE;
            END_IF;
        END_IF;
    END_IF;
END_IF;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_GrantA THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := FALSE;

IF SubsystemBEnable AND CrossReady THEN
    B_DutyNoFeedback(IN := B_Demand AND (NOT B_FailoverActive) AND ((B_Pump1Run AND (NOT B_Pump1Feedback)) OR (B_Pump2Run AND (NOT B_Pump2Feedback))), PT := T#300ms);
    B_StandbyNoFeedback(IN := B_Demand AND B_FailoverActive AND ((B_Pump1Run AND (NOT B_Pump1Feedback)) OR (B_Pump2Run AND (NOT B_Pump2Feedback))), PT := T#300ms);
    IF NOT B_Demand THEN
        B_Pump1Run := FALSE;
        B_Pump2Run := FALSE;
        B_FailoverActive := FALSE;
        IF B_Reset THEN B_Failure := FALSE; END_IF;
    ELSIF NOT B_PrevDemand THEN
        IF B_DutyIsPump1 AND B_Pump1Available THEN
            B_Pump1Run := TRUE; B_Pump2Run := FALSE;
        ELSIF (NOT B_DutyIsPump1) AND B_Pump2Available THEN
            B_Pump1Run := FALSE; B_Pump2Run := TRUE;
        ELSIF B_Pump1Available THEN
            B_Pump1Run := TRUE; B_Pump2Run := FALSE; B_FailoverActive := TRUE;
        ELSIF B_Pump2Available THEN
            B_Pump1Run := FALSE; B_Pump2Run := TRUE; B_FailoverActive := TRUE;
        ELSE
            B_Failure := TRUE;
        END_IF;
    ELSIF B_DutyNoFeedback.Q THEN
        IF B_Pump1Run AND B_Pump2Available AND (NOT B_FailoverActive) THEN
            B_Pump1Run := FALSE; B_Pump2Run := TRUE; B_FailoverActive := TRUE;
        ELSIF B_Pump2Run AND B_Pump1Available AND (NOT B_FailoverActive) THEN
            B_Pump1Run := TRUE; B_Pump2Run := FALSE; B_FailoverActive := TRUE;
        ELSE
            B_Pump1Run := FALSE; B_Pump2Run := FALSE; B_Failure := TRUE;
        END_IF;
    ELSIF B_StandbyNoFeedback.Q THEN
        B_Pump1Run := FALSE; B_Pump2Run := FALSE; B_Failure := TRUE;
    END_IF;
    B_PrevDemand := B_Demand;
ELSE
    B_Pump1Run := FALSE;
    B_Pump2Run := FALSE;
    B_FailoverActive := FALSE;
    B_Failure := FALSE;
END_IF;

END_FUNCTION_BLOCK

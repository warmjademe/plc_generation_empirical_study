FUNCTION_BLOCK C10_B09_composite
VAR_INPUT
    A_Demand : BOOL;
    A_Pump1Available : BOOL;
    A_Pump2Available : BOOL;
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
    A_Pump1Run : BOOL;
    A_Pump2Run : BOOL;
    A_NextPump : INT;
    A_Unavailable : BOOL;
    B_Pump1Run : BOOL;
    B_Pump2Run : BOOL;
    B_FailoverActive : BOOL;
    B_Failure : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_PrevDemand : BOOL;
    B_PrevDemand : BOOL;
    B_DutyNoFeedback : TON;
    B_StandbyNoFeedback : TON;
END_VAR

IF (A_NextPump <> 1) AND (A_NextPump <> 2) THEN
    A_NextPump := 1;
END_IF;
IF A_Reset AND (NOT A_Demand) THEN
    A_NextPump := 1;
END_IF;
IF NOT A_Demand THEN
    A_Pump1Run := FALSE;
    A_Pump2Run := FALSE;
ELSIF NOT A_PrevDemand THEN
    IF (A_NextPump = 1) AND A_Pump1Available THEN
        A_Pump1Run := FALSE;
        A_Pump2Run := FALSE;
        A_NextPump := 2;
    ELSIF A_Pump2Available THEN
        A_Pump1Run := FALSE;
        A_Pump2Run := TRUE;
        A_NextPump := 1;
    ELSIF A_Pump1Available THEN
        A_Pump1Run := TRUE;
        A_Pump2Run := FALSE;
        A_NextPump := 2;
    ELSE
        A_Pump1Run := FALSE;
        A_Pump2Run := FALSE;
    END_IF;
END_IF;
A_Unavailable := A_Demand AND (NOT A_Pump1Available) AND (NOT A_Pump2Available);
A_PrevDemand := A_Demand;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_Pump1Run THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := SubsystemBEnable AND (NOT CrossReady);

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

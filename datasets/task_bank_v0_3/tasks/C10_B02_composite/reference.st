FUNCTION_BLOCK C10_B02_composite
VAR_INPUT
    A_Demand : BOOL;
    A_DutyIsPump1 : BOOL;
    A_Pump1Available : BOOL;
    A_Pump2Available : BOOL;
    A_Pump1Feedback : BOOL;
    A_Pump2Feedback : BOOL;
    A_Reset : BOOL;
    B_Demand : BOOL;
    B_Pump1Available : BOOL;
    B_Pump2Available : BOOL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Pump1Run : BOOL;
    A_Pump2Run : BOOL;
    A_FailoverActive : BOOL;
    A_Failure : BOOL;
    B_Pump1Run : BOOL;
    B_Pump2Run : BOOL;
    B_NextPump : INT;
    B_Unavailable : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_PrevDemand : BOOL;
    A_DutyNoFeedback : TON;
    A_StandbyNoFeedback : TON;
    B_PrevDemand : BOOL;
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
        A_Pump1Run := TRUE; A_Pump2Run := FALSE;
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
    IF (B_NextPump <> 1) AND (B_NextPump <> 2) THEN
        B_NextPump := 1;
    END_IF;
    IF B_Reset AND (NOT B_Demand) THEN
        B_NextPump := 1;
    END_IF;
    IF NOT B_Demand THEN
        B_Pump1Run := FALSE;
        B_Pump2Run := FALSE;
    ELSIF NOT B_PrevDemand THEN
        IF (B_NextPump = 1) AND B_Pump1Available THEN
            B_Pump1Run := TRUE;
            B_Pump2Run := FALSE;
            B_NextPump := 2;
        ELSIF B_Pump2Available THEN
            B_Pump1Run := FALSE;
            B_Pump2Run := TRUE;
            B_NextPump := 1;
        ELSIF B_Pump1Available THEN
            B_Pump1Run := TRUE;
            B_Pump2Run := FALSE;
            B_NextPump := 2;
        ELSE
            B_Pump1Run := FALSE;
            B_Pump2Run := FALSE;
        END_IF;
    END_IF;
    B_Unavailable := B_Demand AND (NOT B_Pump1Available) AND (NOT B_Pump2Available);
    B_PrevDemand := B_Demand;
ELSE
    B_Pump1Run := FALSE;
    B_Pump2Run := FALSE;
    B_NextPump := 0;
    B_Unavailable := FALSE;
END_IF;

END_FUNCTION_BLOCK

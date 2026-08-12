FUNCTION_BLOCK C10_B03_composite
VAR_INPUT
    A_Demand : BOOL;
    A_DutyIsPump1 : BOOL;
    A_Pump1Available : BOOL;
    A_Pump2Available : BOOL;
    A_Pump1Feedback : BOOL;
    A_Pump2Feedback : BOOL;
    A_Reset : BOOL;
    B_LowDemand : BOOL;
    B_HighDemand : BOOL;
    B_LeadIsPump1 : BOOL;
    B_Pump1Available : BOOL;
    B_Pump2Available : BOOL;
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
    B_CapacityShortfall : BOOL;
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
    B_Pump1Run := FALSE;
    B_Pump2Run := FALSE;
    IF B_HighDemand THEN
        B_Pump1Run := B_Pump1Available;
        B_Pump2Run := B_Pump2Available;
    ELSIF B_LowDemand THEN
        IF B_LeadIsPump1 THEN
            IF B_Pump1Available THEN B_Pump1Run := TRUE;
            ELSIF B_Pump2Available THEN B_Pump2Run := TRUE;
            END_IF;
        ELSE
            IF B_Pump2Available THEN B_Pump2Run := TRUE;
            ELSIF B_Pump1Available THEN B_Pump1Run := TRUE;
            END_IF;
        END_IF;
    END_IF;
    B_CapacityShortfall := (B_HighDemand AND ((NOT B_Pump1Available) OR (NOT B_Pump2Available))) OR
        (B_LowDemand AND (NOT B_HighDemand) AND (NOT B_Pump1Available) AND (NOT B_Pump2Available));
ELSE
    B_Pump1Run := FALSE;
    B_Pump2Run := FALSE;
    B_CapacityShortfall := FALSE;
END_IF;

END_FUNCTION_BLOCK

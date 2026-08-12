FUNCTION_BLOCK C10_B13_composite
VAR_INPUT
    A_LowDemand : BOOL;
    A_HighDemand : BOOL;
    A_LeadIsPump1 : BOOL;
    A_Pump1Available : BOOL;
    A_Pump2Available : BOOL;
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
    A_CapacityShortfall : BOOL;
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

A_Pump1Run := FALSE;
A_Pump2Run := FALSE;
IF A_HighDemand THEN
    A_Pump1Run := A_Pump1Available;
    A_Pump2Run := A_Pump2Available;
ELSIF A_LowDemand THEN
    IF A_LeadIsPump1 THEN
        IF A_Pump1Available THEN A_Pump1Run := FALSE;
        ELSIF A_Pump2Available THEN A_Pump2Run := TRUE;
        END_IF;
    ELSE
        IF A_Pump2Available THEN A_Pump2Run := TRUE;
        ELSIF A_Pump1Available THEN A_Pump1Run := TRUE;
        END_IF;
    END_IF;
END_IF;
A_CapacityShortfall := (A_HighDemand AND ((NOT A_Pump1Available) OR (NOT A_Pump2Available))) OR
    (A_LowDemand AND (NOT A_HighDemand) AND (NOT A_Pump1Available) AND (NOT A_Pump2Available));

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

FUNCTION_BLOCK C10_H01_duty_standby_failover
VAR_INPUT
    Demand : BOOL;
    DutyIsPump1 : BOOL;
    Pump1Available : BOOL;
    Pump2Available : BOOL;
    Pump1Feedback : BOOL;
    Pump2Feedback : BOOL;
    Reset : BOOL;
END_VAR
VAR_OUTPUT
    Pump1Run : BOOL;
    Pump2Run : BOOL;
    FailoverActive : BOOL;
    Failure : BOOL;
END_VAR
VAR
    PrevDemand : BOOL;
    DutyNoFeedback : TON;
    StandbyNoFeedback : TON;
END_VAR

DutyNoFeedback(IN := Demand AND (NOT FailoverActive) AND ((Pump1Run AND (NOT Pump1Feedback)) OR (Pump2Run AND (NOT Pump2Feedback))), PT := T#300ms);
StandbyNoFeedback(IN := Demand AND FailoverActive AND ((Pump1Run AND (NOT Pump1Feedback)) OR (Pump2Run AND (NOT Pump2Feedback))), PT := T#300ms);
IF NOT Demand THEN
    Pump1Run := FALSE;
    Pump2Run := FALSE;
    FailoverActive := FALSE;
    IF Reset THEN Failure := FALSE; END_IF;
ELSIF NOT PrevDemand THEN
    IF DutyIsPump1 AND Pump1Available THEN
        Pump1Run := TRUE; Pump2Run := FALSE;
    ELSIF (NOT DutyIsPump1) AND Pump2Available THEN
        Pump1Run := FALSE; Pump2Run := TRUE;
    ELSIF Pump1Available THEN
        Pump1Run := TRUE; Pump2Run := FALSE; FailoverActive := TRUE;
    ELSIF Pump2Available THEN
        Pump1Run := FALSE; Pump2Run := TRUE; FailoverActive := TRUE;
    ELSE
        Failure := TRUE;
    END_IF;
ELSIF DutyNoFeedback.Q THEN
    IF Pump1Run AND Pump2Available AND (NOT FailoverActive) THEN
        Pump1Run := FALSE; Pump2Run := TRUE; FailoverActive := TRUE;
    ELSIF Pump2Run AND Pump1Available AND (NOT FailoverActive) THEN
        Pump1Run := TRUE; Pump2Run := FALSE; FailoverActive := TRUE;
    ELSE
        Pump1Run := FALSE; Pump2Run := FALSE; Failure := TRUE;
    END_IF;
ELSIF StandbyNoFeedback.Q THEN
    Pump1Run := FALSE; Pump2Run := FALSE; Failure := TRUE;
END_IF;
PrevDemand := Demand;

END_FUNCTION_BLOCK

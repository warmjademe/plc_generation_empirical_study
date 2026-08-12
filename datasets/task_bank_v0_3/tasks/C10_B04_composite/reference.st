FUNCTION_BLOCK C10_B04_composite
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
    B_Lead : INT;
    B_Available1 : BOOL;
    B_Available2 : BOOL;
    B_Available3 : BOOL;
    B_Feedback1 : BOOL;
    B_Feedback2 : BOOL;
    B_Feedback3 : BOOL;
    B_Stop : BOOL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Pump1Run : BOOL;
    A_Pump2Run : BOOL;
    A_FailoverActive : BOOL;
    A_Failure : BOOL;
    B_Run1 : BOOL;
    B_Run2 : BOOL;
    B_Run3 : BOOL;
    B_ActiveCount : INT;
    B_Failover : BOOL;
    B_Fault : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_PrevDemand : BOOL;
    A_DutyNoFeedback : TON;
    A_StandbyNoFeedback : TON;
    B_NoFeedback1 : TON;
    B_NoFeedback2 : TON;
    B_NoFeedback3 : TON;
    B_Failed1 : BOOL;
    B_Failed2 : BOOL;
    B_Failed3 : BOOL;
    B_Valid1 : BOOL;
    B_Valid2 : BOOL;
    B_Valid3 : BOOL;
    B_RequiredCount : INT;
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
    B_NoFeedback1(IN := B_Run1 AND (NOT B_Feedback1), PT := T#300ms);
    B_NoFeedback2(IN := B_Run2 AND (NOT B_Feedback2), PT := T#300ms);
    B_NoFeedback3(IN := B_Run3 AND (NOT B_Feedback3), PT := T#300ms);
    IF B_NoFeedback1.Q THEN B_Failed1 := TRUE; END_IF;
    IF B_NoFeedback2.Q THEN B_Failed2 := TRUE; END_IF;
    IF B_NoFeedback3.Q THEN B_Failed3 := TRUE; END_IF;
    IF B_Reset AND (NOT B_LowDemand) AND (NOT B_HighDemand) AND (NOT B_Stop) THEN
        B_Failed1 := FALSE; B_Failed2 := FALSE; B_Failed3 := FALSE; B_Fault := FALSE;
    END_IF;
    B_Run1 := FALSE; B_Run2 := FALSE; B_Run3 := FALSE;
    B_RequiredCount := 0;
    IF B_HighDemand THEN B_RequiredCount := 2;
    ELSIF B_LowDemand THEN B_RequiredCount := 1;
    END_IF;
    B_Valid1 := B_Available1 AND (NOT B_Failed1);
    B_Valid2 := B_Available2 AND (NOT B_Failed2);
    B_Valid3 := B_Available3 AND (NOT B_Failed3);
    IF (NOT B_Stop) AND (B_RequiredCount > 0) THEN
        IF B_Lead = 2 THEN
            IF B_Valid2 THEN B_Run2 := TRUE;
            ELSIF B_Valid3 THEN B_Run3 := TRUE;
            ELSIF B_Valid1 THEN B_Run1 := TRUE;
            END_IF;
            IF B_RequiredCount = 2 THEN
                IF B_Valid3 AND (NOT B_Run3) THEN B_Run3 := TRUE;
                ELSIF B_Valid1 AND (NOT B_Run1) THEN B_Run1 := TRUE;
                ELSIF B_Valid2 AND (NOT B_Run2) THEN B_Run2 := TRUE;
                END_IF;
            END_IF;
        ELSIF B_Lead = 3 THEN
            IF B_Valid3 THEN B_Run3 := TRUE;
            ELSIF B_Valid1 THEN B_Run1 := TRUE;
            ELSIF B_Valid2 THEN B_Run2 := TRUE;
            END_IF;
            IF B_RequiredCount = 2 THEN
                IF B_Valid1 AND (NOT B_Run1) THEN B_Run1 := TRUE;
                ELSIF B_Valid2 AND (NOT B_Run2) THEN B_Run2 := TRUE;
                ELSIF B_Valid3 AND (NOT B_Run3) THEN B_Run3 := TRUE;
                END_IF;
            END_IF;
        ELSE
            IF B_Valid1 THEN B_Run1 := TRUE;
            ELSIF B_Valid2 THEN B_Run2 := TRUE;
            ELSIF B_Valid3 THEN B_Run3 := TRUE;
            END_IF;
            IF B_RequiredCount = 2 THEN
                IF B_Valid2 AND (NOT B_Run2) THEN B_Run2 := TRUE;
                ELSIF B_Valid3 AND (NOT B_Run3) THEN B_Run3 := TRUE;
                ELSIF B_Valid1 AND (NOT B_Run1) THEN B_Run1 := TRUE;
                END_IF;
            END_IF;
        END_IF;
    END_IF;
    B_ActiveCount := 0;
    IF B_Run1 THEN B_ActiveCount := B_ActiveCount + 1; END_IF;
    IF B_Run2 THEN B_ActiveCount := B_ActiveCount + 1; END_IF;
    IF B_Run3 THEN B_ActiveCount := B_ActiveCount + 1; END_IF;
    B_Failover := (B_RequiredCount > 0) AND ((B_ActiveCount < B_RequiredCount) OR ((B_Lead = 1) AND (NOT B_Run1)) OR ((B_Lead = 2) AND (NOT B_Run2)) OR ((B_Lead = 3) AND (NOT B_Run3)));
    IF B_ActiveCount < B_RequiredCount THEN B_Fault := TRUE; END_IF;
ELSE
    B_Run1 := FALSE;
    B_Run2 := FALSE;
    B_Run3 := FALSE;
    B_ActiveCount := 0;
    B_Failover := FALSE;
    B_Fault := FALSE;
END_IF;

END_FUNCTION_BLOCK

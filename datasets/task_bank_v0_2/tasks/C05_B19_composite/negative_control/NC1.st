FUNCTION_BLOCK C05_B19_composite
VAR_INPUT
    A_Start : BOOL;
    A_Stop : BOOL;
    A_Permit : BOOL;
    A_OilPressure : BOOL;
    A_MotorFeedback : BOOL;
    A_Reset : BOOL;
    B_Demand : BOOL;
    B_SafetyTrip : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_LubePump : BOOL;
    A_MotorCommand : BOOL;
    A_Cooldown : BOOL;
    A_Fault : BOOL;
    A_State : INT;
    B_Fan : BOOL;
    B_RunOn : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_PreLube : TON;
    A_FeedbackWait : TON;
    A_CoolTimer : TON;
    B_OffTimer : TOF;
END_VAR

A_PreLube(IN := (A_State = 1) AND A_OilPressure, PT := T#300ms);
A_FeedbackWait(IN := (A_State = 2) AND (NOT A_MotorFeedback), PT := T#400ms);
A_CoolTimer(IN := (A_State = 4), PT := T#300ms);
IF (A_State <> 0) AND (A_State <> 4) AND (A_Stop OR (NOT A_Permit)) THEN
    A_State := 4;
ELSIF (A_State = 3) AND (NOT A_OilPressure) THEN
    A_Fault := FALSE;
    A_State := 4;
ELSIF (A_State = 2) AND A_FeedbackWait.Q THEN
    A_Fault := TRUE;
    A_State := 4;
ELSIF (A_State = 0) AND A_Start AND A_Permit AND (NOT A_Stop) AND (NOT A_Fault) THEN
    A_State := 1;
ELSIF (A_State = 1) AND A_PreLube.Q THEN
    A_State := 2;
ELSIF (A_State = 2) AND A_MotorFeedback THEN
    A_State := 3;
ELSIF (A_State = 4) AND A_CoolTimer.Q THEN
    A_State := 0;
END_IF;
IF A_Reset AND (A_State = 0) AND (NOT A_Start) THEN A_Fault := FALSE; END_IF;
A_LubePump := ((A_State = 1) OR (A_State = 2) OR (A_State = 3) OR (A_State = 4));
A_MotorCommand := ((A_State = 2) OR (A_State = 3)) AND (NOT A_Fault);
A_Cooldown := (A_State = 4);

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_LubePump THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := SubsystemBEnable AND (NOT CrossReady);

IF SubsystemBEnable AND CrossReady THEN
    B_OffTimer(IN := B_Demand AND (NOT B_SafetyTrip), PT := T#300ms);
    IF B_SafetyTrip THEN
        B_Fan := FALSE;
    ELSE
        B_Fan := B_OffTimer.Q;
    END_IF;
    B_RunOn := (NOT B_Demand) AND B_Fan;
ELSE
    B_Fan := FALSE;
    B_RunOn := FALSE;
END_IF;

END_FUNCTION_BLOCK

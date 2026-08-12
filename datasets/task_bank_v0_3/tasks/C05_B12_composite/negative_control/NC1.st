FUNCTION_BLOCK C05_B12_composite
VAR_INPUT
    A_Demand : BOOL;
    A_SafetyTrip : BOOL;
    B_Start : BOOL;
    B_Stop : BOOL;
    B_Permit : BOOL;
    B_OilPressure : BOOL;
    B_MotorFeedback : BOOL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Fan : BOOL;
    A_RunOn : BOOL;
    B_LubePump : BOOL;
    B_MotorCommand : BOOL;
    B_Cooldown : BOOL;
    B_Fault : BOOL;
    B_State : INT;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_OffTimer : TOF;
    B_PreLube : TON;
    B_FeedbackWait : TON;
    B_CoolTimer : TON;
END_VAR

A_OffTimer(IN := A_Demand AND (NOT A_SafetyTrip), PT := T#300ms);
IF A_SafetyTrip THEN
    A_Fan := FALSE;
ELSE
    A_Fan := A_OffTimer.Q;
END_IF;
A_RunOn := (NOT A_Demand) AND A_Fan;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_Fan THEN
    CrossReady := FALSE;
END_IF;
CrossBlocked := SubsystemBEnable AND (NOT CrossReady);

IF SubsystemBEnable AND CrossReady THEN
    B_PreLube(IN := (B_State = 1) AND B_OilPressure, PT := T#300ms);
    B_FeedbackWait(IN := (B_State = 2) AND (NOT B_MotorFeedback), PT := T#400ms);
    B_CoolTimer(IN := (B_State = 4), PT := T#300ms);
    IF (B_State <> 0) AND (B_State <> 4) AND (B_Stop OR (NOT B_Permit)) THEN
        B_State := 4;
    ELSIF (B_State = 3) AND (NOT B_OilPressure) THEN
        B_Fault := TRUE;
        B_State := 4;
    ELSIF (B_State = 2) AND B_FeedbackWait.Q THEN
        B_Fault := TRUE;
        B_State := 4;
    ELSIF (B_State = 0) AND B_Start AND B_Permit AND (NOT B_Stop) AND (NOT B_Fault) THEN
        B_State := 1;
    ELSIF (B_State = 1) AND B_PreLube.Q THEN
        B_State := 2;
    ELSIF (B_State = 2) AND B_MotorFeedback THEN
        IF B_OilPressure THEN
            B_State := 3;
        ELSE
            B_Fault := TRUE;
            B_State := 4;
        END_IF;
    ELSIF (B_State = 4) AND B_CoolTimer.Q THEN
        B_State := 0;
    END_IF;
    IF B_Reset AND (B_State = 0) AND (NOT B_Start) THEN B_Fault := FALSE; END_IF;
    B_LubePump := ((B_State = 1) OR (B_State = 2) OR (B_State = 3) OR (B_State = 4));
    B_MotorCommand := ((B_State = 2) OR (B_State = 3)) AND (NOT B_Fault);
    B_Cooldown := (B_State = 4);
ELSE
    B_LubePump := FALSE;
    B_MotorCommand := FALSE;
    B_Cooldown := FALSE;
    B_Fault := FALSE;
    B_State := 0;
END_IF;

END_FUNCTION_BLOCK

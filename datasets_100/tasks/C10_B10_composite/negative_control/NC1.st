FUNCTION_BLOCK C10_B10_composite
VAR_INPUT
    A_Demand : BOOL;
    A_Pump1Available : BOOL;
    A_Pump2Available : BOOL;
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
    A_NextPump : INT;
    A_Unavailable : BOOL;
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
        A_Pump1Run := TRUE;
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
CrossBlocked := FALSE;

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

FUNCTION_BLOCK C10_B06_composite
VAR_INPUT
    A_RequestA : BOOL;
    A_RequestB : BOOL;
    A_Done : BOOL;
    A_Emergency : BOOL;
    A_Reset : BOOL;
    B_Demand : BOOL;
    B_Pump1Available : BOOL;
    B_Pump2Available : BOOL;
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
    B_NextPump : INT;
    B_Unavailable : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    B_PrevDemand : BOOL;
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

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
END_FUNCTION_BLOCK

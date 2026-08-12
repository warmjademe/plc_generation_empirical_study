FUNCTION_BLOCK C10_X01_three_pump_feedback_dispatch
VAR_INPUT
    LowDemand : BOOL;
    HighDemand : BOOL;
    Lead : INT;
    Available1 : BOOL;
    Available2 : BOOL;
    Available3 : BOOL;
    Feedback1 : BOOL;
    Feedback2 : BOOL;
    Feedback3 : BOOL;
    Stop : BOOL;
    Reset : BOOL;
END_VAR
VAR_OUTPUT
    Run1 : BOOL;
    Run2 : BOOL;
    Run3 : BOOL;
    ActiveCount : INT;
    Failover : BOOL;
    Fault : BOOL;
END_VAR
END_FUNCTION_BLOCK

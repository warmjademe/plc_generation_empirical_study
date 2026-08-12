FUNCTION_BLOCK C08_H02_timed_sequence_fault
VAR_INPUT
    Start : BOOL;
    Sensor1 : BOOL;
    Sensor2 : BOOL;
    Stop : BOOL;
    ResetFault : BOOL;
END_VAR
VAR_OUTPUT
    Actuator1 : BOOL;
    Actuator2 : BOOL;
    Complete : BOOL;
    Fault : BOOL;
    State : INT;
END_VAR
END_FUNCTION_BLOCK

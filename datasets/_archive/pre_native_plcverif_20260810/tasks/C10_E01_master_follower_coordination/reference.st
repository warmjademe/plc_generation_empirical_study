FUNCTION_BLOCK C10_E01_master_follower_coordination
VAR_INPUT
    RunRequest : BOOL;
    MasterReady : BOOL;
    FollowerReady : BOOL;
END_VAR
VAR_OUTPUT
    MasterRun : BOOL;
    FollowerRun : BOOL;
END_VAR

MasterRun := RunRequest AND MasterReady;
FollowerRun := RunRequest AND MasterRun AND FollowerReady;

END_FUNCTION_BLOCK

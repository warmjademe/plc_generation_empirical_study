FUNCTION_BLOCK C01_M01_two_out_of_three_vote
VAR_INPUT
    S1 : BOOL;
    S2 : BOOL;
    S3 : BOOL;
END_VAR
VAR_OUTPUT
    Vote : BOOL;
    Unanimous : BOOL;
END_VAR

Vote := (S1 AND S2) OR (S1 AND S3) OR (S2 AND S3);
Unanimous := (S1 AND S2 AND S3) OR ((NOT S1) AND (NOT S2) AND (NOT S3));

END_FUNCTION_BLOCK

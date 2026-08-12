# Evaluation package separation

- `public_tasks/` is the only tree allowed in model prompts.
- `visible_oracles/` is available to the feedback harness, not to the model.
- `sealed_oracles/` is mounted only by the terminal judge and returns no feedback.
- `qualification_only/` contains reference answers and negative controls.  It is
  used to validate the dataset and must never be mounted in a scored model worker.

There are exactly 50 task IDs in each split.  `reference.st` is not a model input or
an evaluated candidate; it exists only to show that the authored contract is
satisfiable and to calibrate the oracles.

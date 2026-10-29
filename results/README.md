# results/

Only final, reportable results live here. Exploratory and dev runs go to `runs/`, which is not committed.

- `final_runs.jsonl`: hash-chained log of every run on the sealed test split. Created by `python -m evals.run_log append`; checked by `python -m evals.run_log verify` in CI. It does not exist yet because no final run has happened.

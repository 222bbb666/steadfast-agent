# Roadmap

Week 1 starts on 2026-11-02. Two checkpoints matter most: **2026-11-29** (runtime results) and **2026-12-27** (distillation results).

| Week | Ends | Deliverable | Done when |
|---|---|---|---|
| W0 | 11-01 | Repository, frozen split, sealed test split, run log, leakage check, CI | **done**: 18 tests pass |
| W1 | 11-08 | WSL2 Ubuntu with GPU; τ²-bench installed; DeepSeek client (with `reasoning_content` round trip); τ² adapter that drops `task`; B0 and B1 on dev, 3 trials each; measured cost per task | dev numbers and a cost table in `results/dev/` |
| W2 | 11-15 | Failure statistics on dev; choose 2–3 mechanisms; write gate, provenance, receipts; unit tests | each chosen mechanism traced to a failure type ≥5% |
| W3 | 11-22 | Shadow mode; dev iterations; freeze F; LangChain middleware gate and configs L, L+G; start collecting trajectories on the distill split | F frozen at a tagged commit |
| W4 | 11-29 | **Final runtime run** on test; report v1; risk-dial curve | entries in `results/final_runs.jsonl`, chain verifies |
| W5 | 12-06 | Trajectory collection done; SFT data builder (rejection sampling, self-correction segments, dedup, sharegpt format); student baseline on dev | data statistics committed |
| W6 | 12-13 | LoRA SFT on the local RTX 4070 Ti; hyperparameters chosen on dev | training config and seed committed |
| W7 | 12-20 | Freeze the student; **final distillation run** on test (teacher rerun in the same window) | run log entries |
| W8 | 12-27 | Report v2; vLLM + FastAPI demo; blog post | a stranger can reproduce the demo from the README |
| W9+ | 2027-01 | Optional: multi-turn GRPO, or the Chinese language pack and an audit of its tasks | — |

Stop rules: if τ² cannot run or DeepSeek tool calls are incompatible (W1), switch the path or the model; if the dev baseline is above 85% success, the headline becomes cost at equal success; if three dev iterations bring no gain, stop adding mechanisms and report the failure analysis.

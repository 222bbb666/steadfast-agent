# Steadfast（笃行）

**A write-gated agent runtime, distilled into a small model.**

> 慎思之，明辨之，笃行之。 — 《中庸》
> Think carefully, judge clearly, then act with resolve.

LLM agents are fine at *reading*. They break things when they *write*: refunding the wrong order, cancelling the wrong flight, changing a plan the user never confirmed. On τ-bench, each deviation on a state-changing step lowers the odds of success by up to 92% (airline) and 96% (retail), while deviations on read-only steps have little to no effect ([SABER, 2025](https://arxiv.org/abs/2512.07850)).

Steadfast takes that finding seriously:

1. **Runtime.** A hand-written agent loop (no framework in the evaluated path) that puts every write operation through a gate before it touches the world.
2. **Distillation.** Successful, gate-checked trajectories from DeepSeek V4.1-Flash become training data for Qwen3.5-2B, so a model that fits on a 12 GB consumer GPU learns to act like the gated system.
3. **Evidence.** Everything is measured on the official τ²-bench test split, with a sealed test set and a tamper-evident run log, so every number can be audited from git history.

> **Status (2026-10-29): week 0.** The evaluation protocol is frozen and enforced in code. The runtime and the training pipeline are not written yet. No results exist yet, and none are shown below.

---

## What makes it different

| Idea | What it means | Status |
|---|---|---|
| **Write gate** | Only tools that mutate state are gated (declared by the environment, e.g. τ²'s `ToolType.WRITE`). Reads pass freely, so the gate costs nothing where it does not help. | planned (W2) |
| **Write receipts** | Every executed write produces a receipt: which earlier user message or tool result each argument came from, the gate's verdict and reason, tokens and cost. An unexplained argument (an order ID nobody mentioned) is blocked by plain code, no model call needed. | planned (W2) |
| **Shadow mode** | The gate can run observe-only: it records what it *would* have blocked without changing behavior. Its precision is measured this way before it is allowed to act, which is also how you would roll it out in production. | planned (W3) |
| **Risk dial** | One threshold trades *wrong writes* against *wrongly blocked writes*. The report shows the whole curve, so a product owner can pick a point instead of trusting a single score. | planned (W4) |
| **Gate internalization** | The student is trained on successful trajectories *and* on "gate rejected → agent corrected itself" pairs. The question: can a 2B model learn the habit of checking before writing, and keep most of the benefit with the gate switched off? | planned (W6) |
| **Sealed test split** | The 100 test tasks cannot be loaded unless `STEADFAST_FINAL=1`. Every final run is appended to a hash-chained log; editing or deleting an old entry breaks verification. | **done** |
| **No answer leakage** | CI scans the runtime package for benchmark answer fields, `tau2` imports, domain words (English and Chinese) and task IDs. The τ² adapter discards the `task` object, which contains the ground truth. | **done** (scanner); adapter in W1 |

## Results

Filled in only after the final runs. Every number will link to a row in `results/` and to an entry in `results/final_runs.jsonl`.

| Configuration | Model | Avg. success (3 trials) | Wrong-write rate | Cost per solved task |
|---|---|---|---|---|
| Official `llm_agent` (B0) | DeepSeek V4.1-Flash | — | — | — |
| Minimal loop (B1) | DeepSeek V4.1-Flash | — | — | — |
| Steadfast (F) | DeepSeek V4.1-Flash | — | — | — |
| LangGraph `create_agent` (L) | DeepSeek V4.1-Flash | — | — | — |
| Base student | Qwen3.5-2B | — | — | — |
| Distilled student | Qwen3.5-2B + LoRA | — | — | — |

Scores use domestic models for the user simulator and the communication judge, so they are comparable *within this table only*, not with the official leaderboard. See [docs/EVALUATION.md](docs/EVALUATION.md).

## How it fits together

```
 τ²-bench task ──► adapter (drops ground truth) ──► Steadfast runtime ──► DeepSeek V4.1-Flash
                                                     │  read  → execute
                                                     │  write → gate → receipt → execute / reject
                                                     ▼
                                     trajectories + receipts (distill split only)
                                                     ▼
                     LLaMA-Factory LoRA SFT on Qwen3.5-2B  (local RTX 4070 Ti, WSL2)
                                                     ▼
                     vLLM ──► same runtime ──► same sealed test split
```

Details: [docs/DESIGN.md](docs/DESIGN.md).

## Repository map

| Path | What is in it |
|---|---|
| `src/steadfast/` | The runtime. Knows nothing about any benchmark (enforced by `scripts/check_leakage.py`). |
| `evals/` | Split access (test split sealed), final-run log. |
| `integrations/` | τ²-bench adapter, LangChain middleware version of the gate. *(not created yet, W1–W3)* |
| `train/` | Trajectory collection, SFT data building, LLaMA-Factory configs. *(not created yet, W5–W6)* |
| `data/upstream/tau2/` | Official split files copied from τ²-bench at a pinned commit (MIT). |
| `data/splits/tau2-split-v1.json` | The frozen split: dev 36 / distill 142 / test 100. |
| `results/` | Final results and the hash-chained run log. |
| `docs/` | Design, evaluation protocol, roadmap. |

## Quick start

```bash
uv sync                                   # Python 3.12
uv run pytest -q                          # split, sealing, run log, leakage tests
uv run python scripts/make_split.py --check
uv run python scripts/check_leakage.py
uv run python -m evals.run_log verify
```

Copy `.env.example` to `.env` for API keys. Training and vLLM serving run inside WSL2 Ubuntu (vLLM has no native Windows support).

## Stack

DeepSeek V4.1-Flash (agent and teacher) · GLM-5.3-Flash (user simulator) · τ²-bench 2.0 · Qwen3.5-2B · LLaMA-Factory · vLLM · LangChain / LangGraph (comparison baseline and gate middleware) · FastAPI · uv · pytest · GitHub Actions

## Roadmap

Two checkpoints: **2026-11-29** runtime results, **2026-12-27** distillation results. Week-by-week plan in [docs/ROADMAP.md](docs/ROADMAP.md).

## License

MIT. Files under `data/upstream/tau2/` come from [sierra-research/tau2-bench](https://github.com/sierra-research/tau2-bench) (MIT, see the copy of its license in that folder).

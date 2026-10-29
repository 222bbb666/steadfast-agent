# Design

Status: design only. Nothing in this document is implemented yet unless marked **done**.

## 1. Goal

Make a cheap model act safely in multi-turn, tool-using conversations where some actions change the world, and make that safety transferable to a 2B model.

Two measurable questions:

1. Does gating write operations reduce *wrong writes* (a write was executed and the final database state is wrong) without blocking too many correct ones?
2. Can a distilled Qwen3.5-2B keep most of the benefit, and at what cost per solved task?

## 2. The runtime loop

```
for each turn:
    context  = stable prefix (system prompt, policy, tool specs)  +  history  +  facts block
    reply    = model(context)
    if reply is a message to the user          → send it
    if reply is a call to a READ tool           → execute, append result
    if reply is a call to a WRITE tool:
        receipt = provenance(args, history)     # code only: where did each argument come from?
        verdict = gate(policy, facts, call, receipt)
        if verdict.allow                        → execute, append result + receipt
        else                                    → append the rejection reason as feedback, let the model retry or ask the user
```

Reads are never gated. That keeps the extra cost proportional to the number of writes, which is small in customer-service tasks.

## 3. Mechanisms (candidate pool)

A mechanism is only built if the matching failure type is at least 5% of baseline failures on the dev split (decided in W2 from failure statistics, not in advance).

| Mechanism | Type | Description |
|---|---|---|
| Write gate | model call | Checks the proposed write against the policy text and confirmed facts. The model under test is also the default gate model, so "cheap model + good runtime" stays the claim. A different gate model is tried once on dev for comparison. |
| Argument provenance | code | Every ID or amount in a write must appear in an earlier tool result or user message. Unexplained arguments are rejected without a model call. |
| Write vote | model calls | Sample the write step 3 times; execute only if they agree, otherwise ask the user. Targets consistency (pass^k). |
| Read-only finish check | model call | Before ending, check that every request was handled. It may only prompt the agent to ask or to report honestly; it may not add writes. Measured as the false-completion rate. |
| Dual-control wait | code | After asking the user to do something on their device, no write until the user reports back (τ² telecom). |

Engineering features that are always on and reported separately: facts block (only code-verified facts: executed writes, IDs returned by tools), cache-friendly layout (the facts block goes after the history so the prefix stays stable; DeepSeek charges about 50x less for cached input), timeouts and retries identical to τ²'s settings, per-call trace with tokens, cost, latency and the model version returned by the API.

## 4. Creative pieces

**Write receipts.** Each executed write leaves a receipt: the call, where each argument came from, the gate verdict and its reason, token cost. Receipts make the gate auditable and become training data.

**Shadow mode.** The gate runs, logs its verdicts, but never blocks. Comparing shadow verdicts with the final database outcome gives the gate's precision before it is given power. This mirrors how a risky control is rolled out in production.

**Risk dial.** The gate returns a confidence, and one threshold decides when to block. Sweeping the threshold on dev gives a curve of wrong-write rate against wrongly-blocked-write rate. The report shows the curve; the final configuration fixes one point chosen on dev.

**Gate internalization.** The distillation data has two kinds of examples:

1. successful trajectories (rejection sampling: keep only runs the τ² evaluator marks correct);
2. *self-correction* segments: the gate rejected a write, the model then corrected itself, and the run ended correctly. The student learns the corrected behavior, without the gate message in its input.

The experiment then evaluates the student with the gate **off** and **on**. If the student without the gate keeps most of the gated teacher's wrong-write reduction, the habit was learned rather than imposed. This is a hypothesis, not a promised result.

## 5. Frameworks

| Where | What | Why |
|---|---|---|
| Evaluated runtime | Hand-written loop, OpenAI-compatible client (httpx + pydantic) | Ablations need exact control of every call. DeepSeek thinking mode requires `reasoning_content` to be passed back after tool calls or the API returns 400; there are reports of `ChatDeepSeek` dropping that field ([langchain#37390](https://github.com/langchain-ai/langchain/issues/37390)). |
| Comparison | LangGraph `create_agent` with default settings (config L), and the same gate packaged as LangChain middleware (L+G) | Shows what a framework default gets you, and that the gate is portable. Reported descriptively. |
| Fine-tuning | LLaMA-Factory LoRA SFT, sharegpt format with `function_call` / `observation` roles | Loss only on assistant and function-call turns by default, which is what distillation needs. |
| Serving the student | vLLM in WSL2, `--tool-call-parser qwen3_coder --language-model-only` | Official Qwen3.5 serving path; vLLM has no native Windows support. |

## 6. Local training constraints (RTX 4070 Ti, 12 GB)

- Run in WSL2 Ubuntu. Install `flash-linear-attention` (Qwen3.5-2B has 18 Gated DeltaNet layers); a missing fast path was reported to make a training step about 1.7x slower ([transformers#48718](https://github.com/huggingface/transformers/issues/48718)).
- The vocabulary has 248,320 tokens, so an 8K sequence produces about 4 GB of bf16 logits. Use Liger kernels (fused linear cross-entropy, Qwen3.5 supported since Liger 0.8.0), gradient checkpointing, batch size 1 with gradient accumulation, frozen vision encoder.
- Training and vLLM never run at the same time.
- Fallbacks, in order: shorter `cutoff_len`, QLoRA 4-bit, rent a 24 GB GPU.

## 7. Boundaries

- The runtime package `src/steadfast` never imports τ² and never contains domain words or task IDs (`scripts/check_leakage.py`, run in CI).
- The τ² adapter receives the current `task` object, which contains the ground truth, and must discard it.
- Write tools are declared by the environment (τ²'s `ToolType.WRITE`, or service configuration). The runtime does not guess from tool names.

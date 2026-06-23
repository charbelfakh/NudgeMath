# First Live Eval — June 22, 2026

**Model:** llama3.2 · **Provider:** Ollama (local, offline)  
**Commands:** `python -m hint_engine.run_eval` · `python -m hint_engine.model_comparison --models llama3.2 --judge`

## Summary

First live runs of the seed eval harness against a local model — generation-only passes, a self-judged comparison run, then a **neutral-judge experiment** that closes the arc.

**Generation quality was sound:** hints addressed the specific error, stayed within length limits, and the deterministic answer-leakage **text check** passed on every observed hint. Deterministic pass rate varied across four runs (**10/10 → 8/10 → 10/10 → 9/10**) because the model is non-deterministic — not because the gates themselves were flaky.

**Confirmed:** `reveals_answer` self-report is unreliable — the model's boolean self-assessment flips run-to-run while the text check stays stable.

**Overturned (twice):** the design-stage prediction that small local models fail as judges via malformed JSON (`parse_fail`). They produce clean output. And the follow-on reading from the self-judged run — that small models cannot discriminate between hints — was largely a **self-judging artifact**, not a universal small-model trait.

**Final finding:** under a distinct neutral judge (mistral:7b-instruct-q4_K_M), scores spread across **0.50, 0.75, and 1.00** (mean **0.80**) with real per-case differentiation. The compressed 0.50/0.75 band llama3.2 produced judging itself was substantially self-evaluation compression — exactly what the pinned-neutral-judge default and the `*` not-comparable flag were built to guard against.

---

## Deterministic variance (four live runs)

| Run | det pass | notes |
|-----|----------|-------|
| 1 | 10/10 | baseline |
| 2 | 8/10 | gate-level failures on regenerated hints (length/banned phrase), not leakage |
| 3 | 10/10 | |
| 4 | 9/10 | |

**Intermittent self-flag** on `order_of_operations` and `decimal_multiplication` — `reveals_answer=True` on some runs, `False` on others, while the text-leak gate consistently passes. This reinforces Step 3's decision: self-report is **signal, not CI gate**.

| case_id | self-flag observed across runs | text leak (all runs) |
|---------|-------------------------------|----------------------|
| order_of_operations | intermittent True/False | no leak |
| decimal_multiplication | intermittent True/False | no leak |
| all other cases | stable False | no leak |

## Concrete example — `decimal_multiplication`

**Correct answer:** 0.15 (not present in the hint)

**Hint (self-flagged `reveals_answer=True` on one run):**

> The product of two decimal numbers is not always less than one. Reconsider the order in which you are multiplying these values.

A sound hint: names the misconception, nudges toward reordering, does **not** state 0.15. Other runs produced essentially the same hint with `reveals_answer=False`. The deterministic text check passed every time. Only the model's self-assessment flipped.

---

## Self-judged run — wiring confirmed, first prediction corrected

After the Step 8 `config.py` fix:

```powershell
python -m hint_engine.model_comparison --models llama3.2 --judge
```

- Header: **Judge held constant: llama3.2**
- All cells flagged **\*** self-judged (gen model == judge model)
- **`parse_fail 0/10`**, **`judge_ok 10/10`**
- Scores clustered at **0.50** and **0.75** only (mean **0.57**)

**Corrected prediction:** small local models would fail as judges via malformed output. **Wrong.** llama3.2 returned clean rubric JSON on all 10 cases.

**Interim reading (later refined):** flat scoring behind valid output — a subtler failure mode than `parse_fail`. The neutral-judge experiment below revises how much of this was model limitation vs self-judging.

---

## Neutral-judge experiment

### Setup and motivation

To test whether llama3.2's flat self-judged scores reflected a general small-model-judge limitation or **self-preference / self-evaluation bias**, re-ran the harness with a distinct neutral judge:

```powershell
$env:LLM_JUDGE_PROVIDER="ollama"
$env:LLM_JUDGE_MODEL="mistral:7b-instruct-q4_K_M"
python -m hint_engine.model_comparison --models llama3.2 --judge
```

- **Generation:** llama3.2
- **Judge:** mistral:7b-instruct-q4_K_M (7B, distinct model)
- **No `*` self-judged flag** — gen ≠ judge, so scores are comparable unlike the self-judged baseline
- Header: **Judge held constant: mistral:7b-instruct-q4_K_M**

### Result — scores spread under a neutral judge

| case_id | det | judge | score |
|---------|-----|-------|-------|
| algebra_sign_error | PASS | PASS | 1.00 |
| order_of_operations | PASS | PASS | 1.00 |
| fraction_comparison | PASS | FAIL | 0.50 |
| distribute_negative_sign | PASS | PASS | 1.00 |
| combining_unlike_terms | PASS | PASS | 0.75 |
| percentage_confusion | PASS | FAIL | 0.75 |
| units_conversion | PASS | PASS | 0.75 |
| exponent_multiply_rule | PASS | PASS | 1.00 |
| decimal_multiplication | PASS | FAIL | 0.75 |
| fraction_addition | PASS | FAIL | 0.50 |

**Aggregates:** det **10/10**, judge **6/10**, mean score **0.80**, **`parse_fail 0/10`**, **`judge_ok 10/10`**

Scores use three distinct values (**0.50, 0.75, 1.00**) with real per-case spread — vs the two-value band (0.50/0.75, mean 0.57) llama3.2 produced judging itself.

### The finding — self-evaluation compresses scores

A different small model (mistral, 7B) discriminates between hints **perfectly well as a judge** — clean JSON, meaningful score spread. The compressed 0.5/0.75 band was substantially an artifact of **llama3.2 judging its own output**, not a universal small-model trait.

This refines the earlier writeup plainly: the original "small models make poor judges (malformed output)" prediction was **wrong twice over** — they produce clean output (`parse_fail 0`), and at least one (mistral) discriminates well. **The real risk is self-judging, not model size.**

The reading is consistent with self-preference / self-evaluation compression, and demonstrates with live data exactly the bias the pinned-neutral-judge default and the `*` not-comparable flag were designed to handle.

### Two-layer separation confirmed

**det 10/10** while **judge 6/10** — four hints passed all deterministic gates but failed mistral's must-pass rubric items (`addresses_specific_error` and/or `no_semantic_answer_leak`). The deterministic layer caught no leakage; the judge caught hints that **don't address the specific error** — a qualitative failure rules cannot see. This is the gates-vs-judge division of labor working as designed on live output.

### Honest caveats

This is **n=10** seed cases, one generator, two judge models, run a handful of times — illustrative, not statistically robust. The self-preference reading is the most plausible interpretation, not a controlled proof (that would need paired self-vs-neutral runs across more cases and models). Framed here as a real finding from a portfolio-scale eval, with limits stated.

---

## What this tells us

The harness ran live and followed a clear arc:

1. **Predicted** small models judge badly via malformed output → **found** clean JSON instead (`parse_fail 0`).
2. **Predicted** flat scores meant poor discrimination → **found** a neutral judge spreads scores; compression was largely **self-judging**.
3. **Confirmed throughout** that `reveals_answer` self-report is unreliable and that deterministic gates + judge serve different jobs.

**Self-report unreliability (confirmed).** `reveals_answer` stays a model self-report; CI gates on the deterministic text check. `flag_disagreement` surfaces the mismatch live.

**Judge parse failure (predicted, not observed).** Step 7.6's `parse_fail` aggregate remains valuable for models that do fail JSON — llama3.2 and mistral didn't here.

**Self-judging (confirmed as the real comparison risk).** Self-judged runs compress scores into a comfortable band and cannot be read as quality evidence. Cross-model comparison needs a constant external judge — the pinned default and `*` flag exist for that reason, and the neutral-judge experiment shows why.

Generation can be usable offline on a small local model. Meaningful judge scores need a **distinct** judge — and the harness's job is to make each weakness visible as its own signal, not collapse them into a single pass/fail.

# NudgeMath

You are a senior ML/full-stack developer.

## What this is
- A **math-hint generator** that nudges students toward the correct answer without revealing it, plus an **evaluation harness** that scores hint quality against pedagogical rubrics.
- **Contract-first**: shapes are defined once as Python dataclasses and propagated through typed boundaries — Python → Strawberry GraphQL SDL → codegen → TypeScript client. Shape drift is caught at build time, not runtime.
- Stack: Python 3.11 (hint logic + eval) · Strawberry GraphQL 0.319 + FastAPI 0.138 + Uvicorn (API) · Vite 8 + React 19 + TypeScript + Tailwind 4 + Apollo Client 4 + GraphQL Code Generator 7 (frontend).
- LLM access is **provider-agnostic and offline-by-default**: an `LLMClient` Protocol with one `OpenAICompatibleClient` (openai==2.43.0) pointed at Ollama by default (`llama3.2`, no API key), Anthropic's OpenAI-compatible endpoint, etc. Model + provider are **config from env vars**, never hardcoded.
- Human docs: `README.md` (setup/run), `docs/ARCHITECTURE.md` (contract-first design + boundaries), `docs/FIRST_EVAL.md` (first live eval writeup).

## Where things live
- Shapes (source of truth):  `hint_engine/models.py` — `HintRequest`, `Hint`, `EvalCase`, `ConversationTurn`, `CheckResult` dataclasses
- Generation (answer-blind):  `hint_engine/generate.py` — `generate_hint(HintRequest)`; system prompt + strict-JSON parse
- Deterministic gates:        `hint_engine/evaluation.py` — five checks + `EvalReport` / `EvalReport.to_dict()` (the report envelope, and its source of truth)
- LLM-judge:                  `hint_engine/judge.py` — four-item rubric, `JudgeResult`, verdict logic
- Pre-LLM answer gating:      `hint_engine/answer_match.py` — `resolve_correct_answer`, `answers_equivalent` (equivalent forms, conflicting-value rejection)
- Model/provider config:      `hint_engine/config.py` — `ModelConfig`, `LLM_GEN_*` / `LLM_JUDGE_*` resolution, `COMPARISON_PRESETS`, `PINNED_COMPARISON_JUDGE`
- LLM interface:              `hint_engine/llm_client.py` — `LLMClient` Protocol + `OpenAICompatibleClient`
- Shared LLM utils:           `hint_engine/llm_utils.py` — `strip_code_fences`, `meta_from_config`, `MUST_PASS_RUBRIC`
- Seed cases:                 `hint_engine/data/eval_cases.jsonl` (dataset, one case per line) → loaded by `hint_engine/eval_cases.py` into `EVAL_CASES`; `EVAL_CASES[0]` is the canonical `algebra_sign_error` case (tests depend on this order)
- CLI eval runner:            `hint_engine/run_eval.py` — `python -m hint_engine.run_eval [--judge] [--json PATH]`
- Cross-model comparison:     `hint_engine/model_comparison.py` — aggregation layer over `EvalReport` (does not reshape it)
- API:                        `hint_engine/api/schema.py` (Strawberry types + resolvers, `GENERATION_ROOT_TYPES`), `api/app.py` (FastAPI + CORS + GraphQL router), `api/export_schema.py` (SDL export)
- Committed SDL:              `schema.graphql` (repo root) — the codegen source of truth (codegen reads the file, **not** the live endpoint)
- Frontend:                   `frontend/src/components/` — `HintView` (student, multi-turn: accumulates a `history` thread and sends it on follow-up attempts), `EvalView` (admin/portfolio), `EvalReportCard`, `CheckResultRow`, `VerdictBadge`, `MathText` (renders problems/hints accurately: LaTeX via KaTeX + caret `^` superscripts, prose passed through); `src/graphql/operations.graphql` (client ops); `src/generated/` (codegen output, committed); `src/apollo/client.ts`. Any surface that shows a problem/hint/answer goes through `MathText`.
- Python tests:               `tests/` — mock the LLM via `tests/llm_mocks.py` (`MockLLMClient`) + `tests/fixtures_hints.py`

## Commands
- Backend:        `uvicorn hint_engine.api.app:app --reload`  (GraphiQL at `http://127.0.0.1:8000/graphql`; CORS allows `http://localhost:5173`, override via `CORS_ALLOW_ORIGINS`)
- Frontend:       `cd frontend ; npm run dev`  (Vite on `http://localhost:5173`; first time `npm install`)
- Python tests:   `pytest -q`  (from repo root with the venv active; ~78 tests, all LLM calls mocked)
- Lint:           `ruff check .`  (config in `ruff.toml`; `--fix` autofixes imports/ordering)
- Eval (CLI):     `python -m hint_engine.run_eval`  ·  `--judge` adds LLM-judge scoring (slower, real LLM) · `--json PATH` writes the per-case report envelopes as an artifact
- Comparison:     `python -m hint_engine.model_comparison --models llama3.2,sonnet-4.6 --judge`
- SDL re-export:  `python -m hint_engine.api.export_schema > schema.graphql`  (**avoid** PowerShell `Out-File -Encoding utf8` — it writes a BOM that breaks the CI `diff`)
- Codegen:        `cd frontend ; npm run codegen`  (regenerates `src/generated/` from `schema.graphql`)
- Frontend build: `cd frontend ; npm run build`  (runs codegen → `tsc -b` → `vite build`)
- Frontend tests: `cd frontend ; npm test`  (Vitest + React Testing Library, mocked Apollo)
- Offline LLM:    `ollama pull llama3.2`  (default provider; no API key). Anthropic: `$env:LLM_DEFAULT_PROVIDER="anthropic"; $env:ANTHROPIC_API_KEY="..."`

## Conventions (these override casual prompt wording)
- **Never run `git commit` or `git push`** (nor `gh pr create`/merge) — the user owns all commits and pushes. Make and verify changes in the working tree only.
- **Never add AI attribution** — no `Co-Authored-By`, "Generated with", or any co-author/contributor trailer in commit messages, PR bodies, or anything you produce. The user is the sole author.
- **Never commit secrets** — API keys live only in env vars; provider config is `ModelConfig` resolved from the environment, never hardcoded values in code.
- **The answer-blind boundary is sacred.** `generate_hint()` takes only `HintRequest` and must **never** receive `correct_answer`. On the GraphQL generation path, the types in `GENERATION_ROOT_TYPES` (`HintRequestInput`, `HintType`, `HintMetaType`) must expose no answer field. `HintRequestInput.correctAnswer` exists for **teacher-side gating only** — used in the resolver *before* the LLM call, never forwarded to `generate_hint()`. Guarded by `tests/test_api.py::test_generation_path_has_no_correct_answer_on_output`.
- **Contract-first — Python is the source of truth.** Dataclasses in `hint_engine/models.py` and `EvalReport.to_dict()` define the shapes; GraphQL and TypeScript are *derived*, never the reverse. When you change the Python schema: (1) re-export `schema.graphql`, (2) `cd frontend ; npm run codegen`, (3) include the regenerated `schema.graphql` + `frontend/src/generated/` in the **same change**. `EvalReportType` mirrors `EvalReport.to_dict()` field-for-field (hint mirrored at report level as `hintText`/`revealsAnswer`/`meta`; no phantom top-level fields like `deterministicPassed`). Guarded by `test_api.py::test_eval_report_type_fields_match_to_dict_envelope` + the SDL-drift diff.
- **Two eval layers stay separate.** Deterministic gates (`evaluation.py`) are the hard, reproducible, CI-blocking invariants; the LLM-judge (`judge.py`) is advisory qualitative scoring (`MUST_PASS_RUBRIC` = `addresses_specific_error`, `no_semantic_answer_leak`). `deterministic.passed` blocks; root `passed` is the merged human-review verdict. Don't make the judge a build gate.
- **Comparison is an aggregation layer, not a reshape.** `EvalReport` is the per-(case, model) atom with unchanged fields/`to_dict()`. Never fold cross-model columns into `EvalReport` — group flat `list[EvalReport]` in `ComparisonTable` instead.
- **Tests ship with the change** — new module / env knob / gate / route needs a test in the same change; **mock the LLM** (`MockLLMClient`), never hit a live model in tests. Run `pytest -q` before calling work done.
- **Error handling** — surface LLM/parse failures into `Hint.meta["error"]` / `JudgeResult.meta["error"]` (and the typed `meta.error` GraphQL field); don't silently swallow.
- **Deterministic invariants worth knowing**: `MAX_HINT_CHARS = 600`; banned phrases in `evaluation.BANNED_PHRASES`; pure-digit answers are matched on word boundaries with positional phrases ignored (`_POSITIONAL_PREFIX` — "step 7" is not a leak), while tiny numbers 1–5 fall back to substring; a case may opt out of a named gate via `expectations["skip_checks"]` (default: all 5 run).

## Don't touch
- `.venv/`, `frontend/node_modules/`, `.pytest_cache/`, `.vs/`, `__pycache__/` (env / caches — gitignored)
- `frontend/src/generated/` — GraphQL Code Generator output; regenerate with `npm run codegen`, never hand-edit
- `schema.graphql` — derived from the Python schema; regenerate with `export_schema`, never hand-edit

## Maintenance
- When folder structure, commands, conventions, or the type-propagation contract change, update **this file** in the same change.
- Reflect user-facing changes in `README.md` and `docs/ARCHITECTURE.md` in the same change (behavior, structure, commands, boundaries).
- Keep this file concise. If a rule applies to only one folder, prefer `.claude/rules/<name>.md` with `paths:` frontmatter over bloating this file.
- CI: `.github/workflows/ci.yml` runs on every push/PR — four parallel jobs (`lint` = `ruff check .`, `python` = `pytest -q`, `schema` = SDL-drift diff, `frontend` = codegen-committed check + build + Vitest), fully offline (no `ANTHROPIC_API_KEY`). The deterministic gate blocks the build, not the judge. Run these locally before handing off.

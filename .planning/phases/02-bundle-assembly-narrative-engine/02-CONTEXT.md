# Phase 2 Context: Bundle Assembly & Narrative Engine

## Decisions
- **Job Queuing Mechanism:** Postgres Queue. We will create a `jobs` table with `status ENUM('pending', 'in_progress', 'completed', 'failed')`, `retry_count`, and a `payload JSONB` column. This prioritizes durability over latency, which is essential for expensive LLM generations.
- **LangGraph Architecture:** Branched state machine. Narrative sections will be generated in parallel rather than via a linear chain to prevent latency buildup and context degradation.
- **Validation:** Dedicated validation node using the "Generator-Evaluator Pattern". The validation node will verify generated numbers against the raw Decomposer Gold data to reject hallucinations and loop back for correction.
- **Model Selection:** Model-agnostic design (`litellm` or generic wrappers). Default to Claude 3.5 Sonnet for narrative generation (creative/synthesizing) and GPT-4o or GPT-4o-mini for the validation node (logic/numbers).
- **Failure Recovery:** LangGraph native Checkpointing to Postgres. We will rely on LangGraph to persist the state of the graph after every node to recover seamlessly from transient model failures without needing long-term AI memory tools like Mem0.

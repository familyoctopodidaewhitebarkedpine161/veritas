# Veritas Usage Guide

Adversarial parallel verification for AI outputs. One interface, every use case.

---

## Installation

```bash
# From private repo (SSH)
pip install git+ssh://git@github.com/yourorg/veritas.git

# From private repo (HTTPS with token)
pip install git+https://<token>@github.com/yourorg/veritas.git
```

### Environment

```bash
# Required
export ANTHROPIC_API_KEY="sk-ant-..."

# Optional — enables web search for source verification
export BRAVE_API_KEY="..."   # or TAVILY_API_KEY="..."
```

---

## Three Ways to Use Veritas

### 1. Python Library (programmatic use)

```python
from veritas import verify, Verdict

result = await verify("Any claim to check")

print(result)              # REFUTED (0.95) — Summary
result.verdict             # Verdict.REFUTED
result.confidence          # 0.95
result.failure_modes       # [FailureMode(type="factual_error", ...)]
result.report()            # Full markdown report
```

### 2. Claude Code Skill (interactive)

Drop the `skills/verify/` folder into your project or `.claude/` directory. Then:

```
/verify The RAG pipeline says our refund window is 90 days
```

### 3. MCP Server (any AI tool)

Add to `.mcp.json` in your project root:

```json
{
  "mcpServers": {
    "veritas": {
      "command": "python",
      "args": ["-m", "veritas.mcp_server"],
      "env": {
        "ANTHROPIC_API_KEY": "sk-ant-..."
      }
    }
  }
}
```

Works with Claude Desktop, Cursor, Windsurf, or any MCP-compatible tool. The AI tool can then call `verify` as a tool automatically.

### 4. CLI (terminal)

```bash
# Inline
veritas check "The Great Wall is visible from space"

# Verbose with evidence chain
veritas check "..." --verbose

# JSON output for scripting
veritas check "..." --json

# Pipe from another command
cat ai_output.txt | veritas check --stdin

# Interactive shell
veritas shell
```

---

## Integration Patterns

### The Universal Pattern

Regardless of your architecture, the call is always the same:

```python
result = await verify(
    claim=THE_THING_TO_CHECK,
    context=WHERE_IT_CAME_FROM,    # optional
    domain=WHAT_KIND_OF_CONTENT,   # optional
)
```

What changes between use cases is only what you pass as `claim` and `context`.

---

### For RAG Applications

**What to verify:** The generated answer
**What to pass as context:** The retrieved documents

```python
# Your RAG pipeline generates an answer
answer = rag_pipeline.generate(user_query)
docs = rag_pipeline.get_retrieved_documents(user_query)

# Verify the answer against the source documents
result = await verify(
    claim=answer,
    context="\n\n".join(docs),
)

if result.verdict == Verdict.REFUTED:
    # The answer contradicts the source documents
    print(f"Issue: {result.failure_modes[0].detail}")
```

Works with LangChain, LlamaIndex, Haystack, or any RAG framework.

---

### For Agentic Pipelines

**What to verify:** The agent's output before it takes an action
**What to pass as context:** The task description and any intermediate reasoning

```python
# Your agent produces an output
agent_output = agent.run(task)

# Verify before acting on it
result = await verify(
    claim=agent_output,
    context=f"Task: {task}",
    domain="technical",
)

if result.verdict in (Verdict.VERIFIED, Verdict.PARTIAL):
    execute(agent_output)  # Safe to proceed
elif result.verdict == Verdict.REFUTED:
    agent.retry(task, feedback=result.summary)  # Retry with feedback
else:
    flag_for_human_review(agent_output, result)  # Uncertain — escalate
```

Works with CrewAI, AutoGen, LangGraph, or any agent framework.

---

### For Claude Code Skills

**What to verify:** Output from custom skills your team has built
**What to pass as context:** The skill's input/requirements

```bash
# After a skill generates output, verify it
veritas check "$(cat generated_config.yaml)" --domain technical

# Or in Python within the skill itself
result = await verify(
    claim=generated_output,
    context=f"Generated to satisfy: {user_requirements}",
)
```

---

### For CI/CD Quality Gates

**What to verify:** AI-generated content in pull requests
**What to pass as context:** The PR description or source files

```yaml
# .github/workflows/verify.yml
- name: Verify AI content
  run: |
    for file in $(git diff --name-only origin/main -- docs/); do
      veritas check "$(cat $file)" --json >> verify_results.json
    done
```

---

### For Production Middleware

**What to verify:** AI responses before they reach end users
**What to pass as context:** The user's query

```python
# FastAPI example
@app.post("/api/ask")
async def ask(query: str):
    ai_response = model.generate(query)

    result = await verify(claim=ai_response, context=f"User asked: {query}")

    if result.verdict == Verdict.REFUTED:
        return {"error": "Response failed verification", "detail": result.summary}

    return {"answer": ai_response, "confidence": result.confidence}
```

---

### For Batch Evaluation

**What to verify:** A batch of outputs from a model you're evaluating
**What to pass as context:** Optional source documents per item

```python
outputs = model.generate_batch(test_prompts)

for prompt, output in zip(test_prompts, outputs):
    result = await verify(claim=output, context=prompt)
    log(prompt, output, result.verdict, result.confidence)
```

---

## Understanding Results

### Verdicts

| Verdict | What it means | What to do |
|---------|--------------|------------|
| VERIFIED | All agents agree, evidence supports | Safe to use |
| PARTIAL | Some parts correct, some not | Review the failure modes |
| UNCERTAIN | Not enough evidence either way | Get more context or human review |
| DISPUTED | Agents disagree, couldn't resolve | Flag for human review |
| REFUTED | Evidence contradicts the claim | Do not use — check failure modes for why |

### Failure Modes

When something is wrong, Veritas tells you the TYPE of error:

| Type | Meaning | Example |
|------|---------|---------|
| factual_error | A fact is wrong | "Released in 2006" → actually 2007 |
| logical_inconsistency | The reasoning contradicts itself | Premises don't support conclusion |
| unsupported_inference | Claim goes beyond the evidence | Correlation claimed as causation |
| temporal_error | Information is outdated | Using 2020 data for a 2026 claim |
| scope_error | Too broad or too narrow | "All X do Y" when only some do |
| source_conflict | Sources disagree with each other | Two credible sources give different answers |

### Reading the Evidence Chain

```python
for finding in result.evidence:
    print(f"{finding.agent}: {finding.finding} ({finding.confidence:.0%})")
    if finding.reasoning:
        print(f"  Reasoning: {finding.reasoning}")
    if finding.sources:
        print(f"  Sources: {', '.join(finding.sources)}")
```

---

## Configuration

```python
from veritas import Config, verify

config = Config(
    model="claude-sonnet-4-6",       # LLM model
    challenge_round=True,             # Enable challenge round for conflicts
    timeout_seconds=30,               # Per-agent timeout
    verbose=False,                    # Verbose logging
)

result = await verify("claim", config=config)
```

---

## FAQ

**Q: Does it work without a search API key?**
Yes. The source verifier falls back to LLM knowledge. A search key makes it stronger but isn't required.

**Q: How long does verification take?**
~15-20 seconds per claim in isolation mode (4 agents in parallel). Debate mode is ~40s (sequential).

**Q: Can I use a different LLM?**
v1 uses Claude. The provider interface is pluggable — future versions will support OpenAI, Ollama, etc.

**Q: What's the cost per verification?**
~5 LLM calls per claim. With Claude Sonnet 4.6 at $3/$15 per million tokens: roughly $0.05-0.10 per verification.

**Q: Can I verify code, not just text?**
Yes. Pass the code as `claim` and set `domain="technical"`. The logic verifier checks consistency, the adversary looks for edge cases.

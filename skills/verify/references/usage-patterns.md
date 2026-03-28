# Veritas Usage Patterns

Detailed integration patterns for every architecture. The core principle: **the interface is always `verify(claim, context)`** — only what you pass changes.

---

## Installation

### From Private Git Repo

```bash
# SSH (recommended for teams)
pip install git+https://github.com/riaz-sana/veritas.git

# HTTPS with token
pip install git+https://github.com/riaz-sana/veritas.git

# In requirements.txt
git+https://github.com/riaz-sana/veritas.git@main#egg=veritas-verify
```

### Environment Variables

```bash
# Required — Anthropic API key for the verification agents
export ANTHROPIC_API_KEY="sk-ant-..."

# Optional — enables web search for source verification
export BRAVE_API_KEY="..."      # Brave Search
# or
export TAVILY_API_KEY="..."     # Tavily Search

# Optional — override default model
export VERITAS_MODEL="claude-sonnet-4-6"
```

---

## Pattern 1: RAG Application Verification

### The Problem
RAG pipelines retrieve documents and generate answers. The generated answer may hallucinate facts not present in the retrieved documents, or misinterpret the documents.

### The Pattern

```python
import asyncio
from veritas import verify, Verdict

async def verified_rag_query(query: str, rag_pipeline) -> dict:
    """Query RAG pipeline, then verify the response."""
    # Step 1: Get RAG response
    response = rag_pipeline.generate(query)
    retrieved_docs = rag_pipeline.get_retrieved_documents(query)

    # Step 2: Verify — pass the response as claim, docs as context
    result = await verify(
        claim=response,
        context="\n\n---\n\n".join(retrieved_docs),
        domain="technical",
    )

    # Step 3: Act on the verdict
    return {
        "response": response,
        "verified": result.verdict == Verdict.VERIFIED,
        "verdict": result.verdict.value,
        "confidence": result.confidence,
        "issues": [fm.detail for fm in result.failure_modes],
    }

# Usage
result = asyncio.run(verified_rag_query("What is our refund policy?", my_rag))
if not result["verified"]:
    print(f"WARNING: {result['issues']}")
```

### With LangChain

```python
from langchain.chains import RetrievalQA
from veritas import verify, Verdict

async def verified_langchain_query(chain: RetrievalQA, query: str):
    response = chain.invoke(query)
    result = await verify(
        claim=response["result"],
        context="\n".join(doc.page_content for doc in response["source_documents"]),
    )
    return response["result"] if result.verdict != Verdict.REFUTED else None
```

### With LlamaIndex

```python
from llama_index.core import VectorStoreIndex
from veritas import verify

async def verified_llamaindex_query(index: VectorStoreIndex, query: str):
    response = index.as_query_engine().query(query)
    result = await verify(
        claim=str(response),
        context="\n".join(node.text for node in response.source_nodes),
    )
    return {"answer": str(response), "verdict": result.verdict.value}
```

---

## Pattern 2: Agentic Pipeline Verification

### The Problem
AI agents take actions based on their reasoning. If the agent's reasoning is wrong, the action is wrong. Verify before acting.

### Pre-Action Gate

```python
from veritas import verify, Verdict

async def verified_agent_step(agent, task: str):
    """Run agent, verify its output, retry if wrong."""
    output = agent.run(task)

    result = await verify(
        claim=output,
        domain="technical",
    )

    if result.verdict in (Verdict.VERIFIED, Verdict.PARTIAL):
        return output  # Safe to proceed

    if result.verdict == Verdict.REFUTED:
        # Retry with feedback
        feedback = f"Your output was incorrect: {result.summary}"
        return agent.run(task, feedback=feedback)

    # UNCERTAIN or DISPUTED — flag for human review
    return {"output": output, "needs_review": True, "reason": result.summary}
```

### Multi-Step Pipeline

```python
async def verified_pipeline(steps: list[callable], input_data):
    """Run a multi-step pipeline with verification between steps."""
    current = input_data

    for i, step in enumerate(steps):
        output = step(current)

        result = await verify(
            claim=str(output),
            context=f"Pipeline step {i+1}. Input was: {str(current)[:500]}",
        )

        if result.verdict == Verdict.REFUTED:
            raise PipelineError(
                f"Step {i+1} produced incorrect output: {result.summary}"
            )

        current = output

    return current
```

### With CrewAI

```python
from crewai import Agent, Task, Crew
from veritas import verify, Verdict

async def verified_crew_output(crew: Crew, inputs: dict):
    result = crew.kickoff(inputs=inputs)
    verification = await verify(
        claim=result.raw,
        domain="technical",
    )
    return {
        "output": result.raw,
        "verified": verification.verdict != Verdict.REFUTED,
        "confidence": verification.confidence,
        "failure_modes": [fm.type.value for fm in verification.failure_modes],
    }
```

---

## Pattern 3: Claude Code Skill Output Verification

### The Problem
Colleagues build custom Claude Code skills that generate outputs (code, configs, docs). Verify those outputs are correct.

### Verify Skill Output

```python
# In your skill's workflow, after generating output:
from veritas import verify

async def verify_generated_config(config_text: str, requirements: str):
    """Verify a generated configuration matches requirements."""
    result = await verify(
        claim=config_text,
        context=f"This config was generated to satisfy: {requirements}",
        domain="technical",
    )
    return result
```

### As a Post-Skill Check

```bash
# After any skill generates output, run verification
veritas check "$(cat generated_output.txt)" --domain technical --verbose
```

---

## Pattern 4: CI/CD Quality Gate

### The Problem
AI-generated content (docs, changelogs, release notes) goes through CI. Verify accuracy before merge.

### GitHub Actions

```yaml
# .github/workflows/verify-ai-content.yml
name: Verify AI Content
on: pull_request

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install Veritas
        run: pip install git+https://github.com/riaz-sana/veritas.git

      - name: Verify AI-generated docs
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          # Find AI-generated files and verify each
          for file in $(git diff --name-only origin/main -- docs/); do
            echo "Verifying $file..."
            veritas check "$(cat $file)" --domain technical --json > "/tmp/verify_${file##*/}.json"
          done
```

### Pre-Commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit
# Verify AI-generated content before committing

for file in $(git diff --cached --name-only -- "*.md" "*.txt"); do
    verdict=$(veritas check "$(cat "$file")" --json 2>/dev/null | jq -r '.verdict')
    if [ "$verdict" = "REFUTED" ]; then
        echo "BLOCKED: $file contains factual errors"
        exit 1
    fi
done
```

---

## Pattern 5: Production Middleware

### The Problem
AI responses go to end users in production. Add a verification layer before responses are served.

### FastAPI Middleware

```python
from fastapi import FastAPI, Request
from veritas import verify, Verdict

app = FastAPI()

@app.middleware("http")
async def verify_ai_responses(request: Request, call_next):
    response = await call_next(request)

    # Only verify AI-generated endpoints
    if request.url.path.startswith("/api/ai/"):
        body = await response.body()
        ai_content = body.decode()

        result = await verify(claim=ai_content)

        # Add verification headers
        response.headers["X-Veritas-Verdict"] = result.verdict.value
        response.headers["X-Veritas-Confidence"] = str(result.confidence)

        if result.verdict == Verdict.REFUTED:
            return JSONResponse(
                status_code=422,
                content={"error": "AI response failed verification", "detail": result.summary},
            )

    return response
```

### Flask Decorator

```python
from functools import wraps
from veritas import verify, Verdict
import asyncio

def verified(f):
    """Decorator to verify AI-generated responses."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        response = f(*args, **kwargs)
        result = asyncio.run(verify(claim=str(response)))
        if result.verdict == Verdict.REFUTED:
            return {"error": result.summary}, 422
        return response
    return wrapper

@app.route("/api/answer")
@verified
def get_answer():
    return ai_model.generate(request.args["q"])
```

---

## Pattern 6: Batch Evaluation

### The Problem
Evaluate a batch of AI outputs (e.g., after fine-tuning, before deployment of a new model version).

### Batch Verify

```python
import asyncio
from veritas import verify, Verdict

async def batch_verify(outputs: list[dict]) -> dict:
    """Verify a batch of AI outputs, return summary stats."""
    results = []
    for item in outputs:
        r = await verify(
            claim=item["output"],
            context=item.get("context", ""),
            domain=item.get("domain", "general"),
        )
        results.append({
            "input": item.get("input", ""),
            "output": item["output"],
            "verdict": r.verdict.value,
            "confidence": r.confidence,
            "failure_modes": [fm.type.value for fm in r.failure_modes],
        })

    total = len(results)
    verified = sum(1 for r in results if r["verdict"] == "VERIFIED")
    refuted = sum(1 for r in results if r["verdict"] == "REFUTED")

    return {
        "total": total,
        "verified": verified,
        "refuted": refuted,
        "accuracy": verified / total if total else 0,
        "results": results,
    }
```

---

## Pattern 7: MCP Server Integration

### For Any AI Tool (Claude Desktop, Cursor, Windsurf, etc.)

Add to your `.mcp.json`:

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

The AI tool can then call `verify` as a tool automatically.

---

## The Universal Pattern

Regardless of architecture, the call is always:

```python
result = await verify(
    claim=THE_THING_TO_CHECK,       # What did the AI say?
    context=WHERE_IT_CAME_FROM,     # What was the source/prompt/docs?
    domain=WHAT_KIND_OF_CONTENT,    # What domain is this?
)

if result.verdict == Verdict.REFUTED:
    # Handle the error — result.failure_modes tells you WHY
    ...
```

That's it. Same three lines for RAG, agents, skills, CI/CD, production, batch eval.

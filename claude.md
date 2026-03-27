# Veritas — Build Brief

## What we're building
A standalone open-source Python library for adversarial parallel verification of AI outputs.
No ground truth required. Model-agnostic. pip-installable.

## Core interface
```python
from veritas import verify
result = verify(claim="...", context="...", domain="technical")
# Returns: verdict, confidence, evidence, failure_modes, report
```

## Agent swarm (via Overstory)
- Logic verifier — internal consistency
- Source verifier — factual cross-reference via web search  
- Adversary — constructs counterexamples
- Calibration agent — confidence vs evidence alignment
- Synthesiser — aggregates all into structured verdict

## Key constraint
Agents run in parallel with NO shared context until synthesis. Prevents cross-contamination.

## Output format
VERIFIED / PARTIAL / UNCERTAIN / DISPUTED + confidence score + evidence chain + failure modes

## Stack
- Python library (pip installable)
- Overstory for multi-agent orchestration
- Claude Code as agent runtime
- SQLite for inter-agent messaging (via Overstory)
- Structured JSON output

## Closest existing thing
ThoughtProof MCP — paywalled, black-box, no evidence chain, not open source. We beat it on all counts.
```

Then in Claude Code, start with:
```
Read VERITAS_BRIEF.md and scaffold the project structure for the Veritas library. 
Then initialize Overstory and write the task specs for all 5 agents.
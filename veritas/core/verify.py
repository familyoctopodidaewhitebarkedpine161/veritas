"""Main verify() function — public entry point for Veritas."""
from __future__ import annotations
from veritas.core.config import Config, VeritasConfigError
from veritas.core.result import VerificationResult
from veritas.orchestration.runner import VerificationRunner
from veritas.providers.claude import ClaudeProvider
from veritas.providers.search import BraveSearchProvider, TavilySearchProvider

async def verify(
    claim: str, context: str | None = None, domain: str | None = None,
    references: list[str] | None = None, model: str | None = None,
    config: Config | None = None,
) -> VerificationResult:
    """Verify a claim using adversarial parallel verification.

    Args:
        claim: The claim or AI output to verify.
        context: Optional source documents or surrounding context.
        domain: Optional domain hint (technical, scientific, medical, legal, general).
        references: Optional list of reference document paths.
        model: Optional model override.
        config: Optional full configuration object.
    """
    if not claim or not claim.strip():
        raise ValueError("claim must be a non-empty string")
    if config is None:
        config = Config()
    if model:
        config.model = model
    config.validate()
    llm_provider = ClaudeProvider(model=config.model, api_key=config.anthropic_api_key)
    if config.search_provider == "tavily":
        search_provider = TavilySearchProvider(api_key=config.search_api_key)
    else:
        search_provider = BraveSearchProvider(api_key=config.search_api_key)
    runner = VerificationRunner(llm_provider=llm_provider, search_provider=search_provider, config=config)
    return await runner.run(claim=claim, context=context, domain=domain, references=references or [])

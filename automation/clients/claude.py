"""Anthropic Claude API wrapper - utilise pour blog SEO, FAQ, descriptions produits."""
import logging
from typing import Optional

logger = logging.getLogger("automation.clients.claude")


_FALLBACK_KEYWORDS = (
    "credit",
    "rate",
    "quota",
    "billing",
    "insufficient",
    "overloaded",
    "exceeded",
)


class ClaudeClient:
    def __init__(
        self,
        api_key: str,
        default_model: str = "claude-sonnet-4-5-20250929",
        fallback=None,
    ):
        self.api_key = api_key
        self.default_model = default_model
        self._client = None
        self._fallback = fallback

    def _get_client(self):
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 1.0,
    ) -> str:
        """Renvoie le texte genere. Fallback Kie.ai sur erreur quota."""
        client = self._get_client()
        model = model or self.default_model
        try:
            msg = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            text = msg.content[0].text
            logger.info(
                "Claude OK : model=%s, %d chars", model, len(text)
            )
            return text
        except Exception as e:
            err = str(e).lower()
            if self._fallback and any(kw in err for kw in _FALLBACK_KEYWORDS):
                logger.warning("Claude credit/quota error -> fallback Kie.ai")
                return self._fallback.generate(
                    system_prompt, user_prompt, max_tokens=max_tokens
                )
            raise

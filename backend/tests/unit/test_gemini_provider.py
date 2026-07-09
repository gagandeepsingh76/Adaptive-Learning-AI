"""Gemini generation adapter tests without network access."""

from types import SimpleNamespace

from app.ai.gemini import GeminiProvider
from app.core.interfaces.ai import GenerationRequest


class FakeModels:
    def __init__(self) -> None:
        self.config = None

    async def generate_content(self, *, model, contents, config):
        self.config = config
        assert model == "gemini-2.5-flash"
        assert contents == "prompt"
        return SimpleNamespace(
            text='{"ok":true}',
            usage_metadata=SimpleNamespace(
                prompt_token_count=7, candidates_token_count=3, total_token_count=10
            ),
            candidates=[SimpleNamespace(finish_reason=SimpleNamespace(value="STOP"))],
        )


async def test_gemini_provider_normalizes_usage_and_json_config(ai_settings) -> None:
    models = FakeModels()
    client = SimpleNamespace(aio=SimpleNamespace(models=models))
    provider = GeminiProvider("", ai_settings, client=client)

    result = await provider.generate(
        GenerationRequest(prompt="prompt", response_schema={"type": "object"})
    )

    assert result.text == '{"ok":true}'
    assert result.usage.total_tokens == 10
    assert models.config.response_mime_type == "application/json"


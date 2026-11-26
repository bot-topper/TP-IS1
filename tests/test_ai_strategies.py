"""Pruebas unitarias para la interfaz AnswerIA y sus estrategias concretas."""

from dataclasses import dataclass

import pytest

from myapp.services.ai.strategies import (
    AnswerGemini,
    AnswerIA,
    AnswerOpenAI,
    LocalModelAnswer,
)


@dataclass
class _FakeQuestion:
    title: str
    body: str


class _ForumAssistantContext:
    """Contexto de ejemplo que delega la generación de respuestas en AnswerIA."""

    def __init__(self, strategy: AnswerIA) -> None:
        self.strategy = strategy

    def set_strategy(self, strategy: AnswerIA) -> None:
        self.strategy = strategy

    def generate_answer(self, question: _FakeQuestion) -> str:
        return self.strategy.answer(question)


def test_answer_ia_is_abstract_interface() -> None:
    with pytest.raises(TypeError):
        AnswerIA()  # type: ignore[abstract]


def test_concrete_strategies_implement_answer_ia(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")

    openai_strategy = AnswerOpenAI()
    gemini_strategy = AnswerGemini()
    local_strategy = LocalModelAnswer()

    assert isinstance(openai_strategy, AnswerIA)
    assert isinstance(gemini_strategy, AnswerIA)
    assert isinstance(local_strategy, AnswerIA)


def test_strategies_require_credentials_without_hardcoding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        AnswerOpenAI()

    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        AnswerGemini()


def test_strategies_configure_via_params_and_hide_credentials_in_repr() -> None:
    openai_secret = "sk-secret-openai-123"
    gemini_secret = "AIza-secret-gemini-456"

    openai_strategy = AnswerOpenAI(api_key=openai_secret, model="gpt-4.1-mini")
    gemini_strategy = AnswerGemini(api_key=gemini_secret, model="gemini-2.5-pro")
    local_strategy = LocalModelAnswer(
        model="mistral", base_url="http://127.0.0.1:11434/api/generate"
    )

    assert openai_strategy.model == "gpt-4.1-mini"
    assert gemini_strategy.model == "gemini-2.5-pro"
    assert local_strategy.model == "mistral"
    assert openai_secret not in repr(openai_strategy)
    assert gemini_secret not in repr(gemini_strategy)


def test_strategies_configure_via_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "env-openai-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o")
    monkeypatch.setenv("GEMINI_API_KEY", "env-gemini-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash")
    monkeypatch.setenv("LOCAL_MODEL_NAME", "qwen2.5")
    monkeypatch.setenv("LOCAL_MODEL_URL", "http://localhost:8080/api/generate")

    openai_strategy = AnswerOpenAI()
    gemini_strategy = AnswerGemini()
    local_strategy = LocalModelAnswer()

    assert openai_strategy.model == "gpt-4o"
    assert gemini_strategy.model == "gemini-2.5-flash"
    assert local_strategy.model == "qwen2.5"
    assert local_strategy.base_url == "http://localhost:8080/api/generate"


def test_openai_strategy_builds_request_and_parses_response() -> None:
    captured: dict[str, object] = {}

    def fake_transport(url, payload, headers, timeout):
        captured["url"] = url
        captured["payload"] = payload
        captured["headers"] = headers
        return {"choices": [{"message": {"content": "  Usa el patrón Strategy.  "}}]}

    strategy = AnswerOpenAI(
        api_key="test-openai-key",
        model="gpt-4o-mini",
        transport=fake_transport,
    )
    question = _FakeQuestion(title="Patrón Strategy", body="¿Cuándo conviene usarlo?")

    result = strategy.answer(question)

    assert result == "Usa el patrón Strategy."
    assert captured["url"] == "https://api.openai.com/v1/chat/completions"
    assert captured["headers"] == {"Authorization": "Bearer test-openai-key"}
    assert captured["payload"] == {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "user",
                "content": "Título: Patrón Strategy\nContenido: ¿Cuándo conviene usarlo?",
            }
        ],
    }


def test_gemini_strategy_builds_request_and_parses_response() -> None:
    captured: dict[str, object] = {}

    def fake_transport(url, payload, headers, timeout):
        captured["url"] = url
        captured["payload"] = payload
        captured["headers"] = headers
        return {
            "candidates": [
                {"content": {"parts": [{"text": "Respuesta desde Gemini."}]}}
            ]
        }

    strategy = AnswerGemini(
        api_key="test-gemini-key",
        model="gemini-2.5-flash",
        transport=fake_transport,
    )
    question = _FakeQuestion(title="Python ABC", body="¿Cómo definir interfaces?")

    result = strategy.answer(question)

    assert result == "Respuesta desde Gemini."
    assert (
        captured["url"]
        == "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
    )
    assert captured["headers"] == {"x-goog-api-key": "test-gemini-key"}
    assert captured["payload"] == {
        "contents": [
            {
                "parts": [
                    {"text": "Título: Python ABC\nContenido: ¿Cómo definir interfaces?"}
                ]
            }
        ]
    }


def test_local_model_strategy_builds_request_and_parses_response() -> None:
    captured: dict[str, object] = {}

    def fake_transport(url, payload, headers, timeout):
        captured["url"] = url
        captured["payload"] = payload
        return {"response": "Respuesta local con Ollama."}

    strategy = LocalModelAnswer(
        model="llama3",
        base_url="http://localhost:11434/api/generate",
        transport=fake_transport,
    )
    question = _FakeQuestion(title="SQLite", body="¿Cómo correr tests en memoria?")

    result = strategy.answer(question)

    assert result == "Respuesta local con Ollama."
    assert captured["url"] == "http://localhost:11434/api/generate"
    assert captured["payload"] == {
        "model": "llama3",
        "prompt": "Título: SQLite\nContenido: ¿Cómo correr tests en memoria?",
        "stream": False,
    }


def test_dynamic_runtime_strategy_exchange() -> None:
    question = _FakeQuestion(
        title="Desacoplar LLM",
        body="¿Cómo cambiar de proveedor sin tocar el foro?",
    )

    openai_strategy = AnswerOpenAI(
        api_key="key-openai",
        transport=lambda url, payload, headers, timeout: {
            "choices": [{"message": {"content": "Respuesta OpenAI"}}]
        },
    )
    gemini_strategy = AnswerGemini(
        api_key="key-gemini",
        transport=lambda url, payload, headers, timeout: {
            "candidates": [{"content": {"parts": [{"text": "Respuesta Gemini"}]}}]
        },
    )
    local_strategy = LocalModelAnswer(
        transport=lambda url, payload, headers, timeout: {
            "response": "Respuesta Local"
        },
    )

    assistant = _ForumAssistantContext(strategy=openai_strategy)
    assert assistant.generate_answer(question) == "Respuesta OpenAI"

    assistant.set_strategy(gemini_strategy)
    assert assistant.generate_answer(question) == "Respuesta Gemini"

    assistant.set_strategy(local_strategy)
    assert assistant.generate_answer(question) == "Respuesta Local"


def test_invalid_question_raises_value_error() -> None:
    strategy = LocalModelAnswer(
        transport=lambda url, payload, headers, timeout: {"response": "ok"}
    )

    with pytest.raises(ValueError):
        strategy.answer(None)  # type: ignore[arg-type]

    with pytest.raises(ValueError):
        strategy.answer(_FakeQuestion(title="   ", body="Contenido válido"))

    with pytest.raises(ValueError):
        strategy.answer(_FakeQuestion(title="Título válido", body=""))

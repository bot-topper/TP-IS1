"""Strategies intercambiables de IA para responder preguntas"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, Protocol


class QuestionLike(Protocol):
    """Contrato de una pregunta del foro."""

    title: str
    body: str


HttpTransport = Callable[[str, dict[str, Any], dict[str, str], float], dict[str, Any]]


def _default_http_post(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout: float,
) -> dict[str, Any]:
    """Envía una petición HTTP POST con JSON y retorna la respuesta decodificada."""
    data = json.dumps(payload).encode("utf-8")
    request_headers = {"Content-Type": "application/json", **headers}
    req = urllib.request.Request(url, data=data, headers=request_headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Error HTTP {exc.code} al consultar el proveedor IA: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Error de conexión con el proveedor IA: {exc.reason}") from exc


def _build_prompt(question: QuestionLike) -> str:
    """Valida la pregunta y construye el prompt estándar para los modelos."""
    if question is None:
        raise ValueError("La pregunta no puede ser nula.")

    title = getattr(question, "title", None)
    if not isinstance(title, str) or not title.strip():
        raise ValueError("La pregunta debe tener un título no vacío.")
    body = getattr(question, "body", None)
    if not isinstance(body, str) or not body.strip():
        raise ValueError("La pregunta debe tener un cuerpo no vacío.")

    return f"Título: {title.strip()}\nContenido: {body.strip()}"


def _resolve_required_secret(value: str | None, env_var: str) -> str:
    """Obtiene una credencial desde parámetro o variable de entorno sin hardcodearla."""
    resolved = value if value is not None else os.getenv(env_var)
    if not resolved or not resolved.strip():
        raise ValueError(
            f"Falta configurar la credencial requerida ({env_var})."
        )
    return resolved.strip()


def _resolve_setting(value: str | None, env_var: str, default: str) -> str:
    """Obtiene un parámetro de configuración desde argumento, entorno o valor por defecto."""
    resolved = value if value is not None else os.getenv(env_var, default)
    if not resolved or not resolved.strip():
        raise ValueError(f"El parámetro de configuración ({env_var}) no puede estar vacío.")
    return resolved.strip()


def _extract_text_response(content: object, provider: str) -> str:
    """Valida que el contenido devuelto por el proveedor sea texto."""
    if not isinstance(content, str):
        raise TypeError(f"Respuesta inválida del proveedor {provider}.")
    return content.strip()


class AnswerIA(ABC):
    """Interfaz Strategy para proveedores de modelos de lenguaje."""

    @abstractmethod
    def answer(self, question: QuestionLike) -> str:
        """Genera una respuesta en texto para la pregunta dada."""


class AnswerOpenAI(AnswerIA):
    """Estrategia concreta que consulta la API de OpenAI."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout: float = 30.0,
        transport: HttpTransport | None = None,
    ) -> None:
        self._api_key = _resolve_required_secret(api_key, "OPENAI_API_KEY")
        self.model = _resolve_setting(model, "OPENAI_MODEL", "gpt-4o-mini")
        self.base_url = _resolve_setting(
            base_url, "OPENAI_BASE_URL", "https://api.openai.com/v1"
        ).rstrip("/")
        self.timeout = timeout
        self._transport = transport or _default_http_post

    def __repr__(self) -> str:
        return f"AnswerOpenAI(model={self.model!r}, base_url={self.base_url!r})"

    def answer(self, question: QuestionLike) -> str:
        prompt = _build_prompt(question)
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
        }
        headers = {"Authorization": f"Bearer {self._api_key}"}
        data = self._transport(url, payload, headers, self.timeout)

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError("Respuesta inválida del proveedor OpenAI.") from exc
        return _extract_text_response(content, "OpenAI")


class AnswerGemini(AnswerIA):
    """Estrategia concreta que consulta la API de Google Gemini."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout: float = 30.0,
        transport: HttpTransport | None = None,
    ) -> None:
        self._api_key = _resolve_required_secret(api_key, "GEMINI_API_KEY")
        self.model = _resolve_setting(model, "GEMINI_MODEL", "gemini-2.5-flash")
        self.base_url = _resolve_setting(
            base_url,
            "GEMINI_BASE_URL",
            "https://generativelanguage.googleapis.com/v1beta",
        ).rstrip("/")
        self.timeout = timeout
        self._transport = transport or _default_http_post

    def __repr__(self) -> str:
        return f"AnswerGemini(model={self.model!r}, base_url={self.base_url!r})"

    def answer(self, question: QuestionLike) -> str:
        prompt = _build_prompt(question)
        url = f"{self.base_url}/models/{self.model}:generateContent"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
        }
        headers = {"x-goog-api-key": self._api_key}
        data = self._transport(url, payload, headers, self.timeout)

        try:
            content = data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError("Respuesta inválida del proveedor Gemini.") from exc
        return _extract_text_response(content, "Gemini")


class LocalModelAnswer(AnswerIA):
    """Estrategia concreta para un modelo de lenguaje ejecutado localmente."""

    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
        timeout: float = 30.0,
        transport: HttpTransport | None = None,
    ) -> None:
        self.model = _resolve_setting(model, "LOCAL_MODEL_NAME", "llama3")
        self.base_url = _resolve_setting(
            base_url,
            "LOCAL_MODEL_URL",
            "http://localhost:11434/api/generate",
        ).rstrip("/")
        self.timeout = timeout
        self._transport = transport or _default_http_post

    def __repr__(self) -> str:
        return f"LocalModelAnswer(model={self.model!r}, base_url={self.base_url!r})"

    def answer(self, question: QuestionLike) -> str:
        prompt = _build_prompt(question)
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        data = self._transport(self.base_url, payload, {}, self.timeout)

        content = data.get("response") if isinstance(data, dict) else None
        return _extract_text_response(content, "de modelo local")

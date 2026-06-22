import json
import logging
from typing import AsyncGenerator, Dict, List
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

# Try these models in order until one works
GEMINI_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
    "gemini-1.0-pro",
]


class LLMService:
    def __init__(self):
        self.ollama_model = "llama3"

    # ── Public API ────────────────────────────────────────────────────────────

    async def generate_response(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
        if settings.GEMINI_API_KEY:
            for model in GEMINI_MODELS:
                try:
                    result = await self._call_gemini(model, messages, temperature)
                    if result:
                        return result
                except httpx.HTTPStatusError as e:
                    if e.response.status_code in (429, 503):
                        logger.warning(f"Gemini {model} overloaded ({e.response.status_code}), trying next...")
                        continue
                    logger.error(f"Gemini {model} error: {e}")
                    break
                except Exception as e:
                    logger.error(f"Gemini {model} failed: {e}")
                    break

        try:
            return await self._call_ollama(messages, temperature)
        except Exception as e:
            logger.error(f"Ollama failed: {e}")
            return (
                "I'm temporarily unable to generate a response. "
                "The AI service is overloaded — please try again in a few seconds."
            )

    async def stream_response(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> AsyncGenerator[str, None]:
        if settings.GEMINI_API_KEY:
            for model in GEMINI_MODELS:
                try:
                    collected = ""
                    async for chunk in self._stream_gemini(model, messages, temperature):
                        collected += chunk
                        yield chunk
                    if collected:
                        return
                except httpx.HTTPStatusError as e:
                    if e.response.status_code in (429, 503):
                        logger.warning(f"Gemini stream {model} overloaded, trying next...")
                        continue
                    logger.error(f"Gemini stream {model} HTTP error: {e}")
                    break
                except Exception as e:
                    logger.error(f"Gemini stream {model} failed: {e}")
                    break

        try:
            async for chunk in self._stream_ollama(messages, temperature):
                yield chunk
        except Exception as e:
            logger.error(f"Ollama stream failed: {e}")
            yield (
                "I'm temporarily unable to generate a response. "
                "The AI service is overloaded — please try again in a few seconds."
            )

    # ── Gemini ────────────────────────────────────────────────────────────────

    def _build_gemini_payload(self, messages: List[Dict[str, str]], temperature: float) -> Dict:
        contents = []
        system_instruction = None
        for msg in messages:
            if msg["role"] == "system":
                system_instruction = {"parts": [{"text": msg["content"]}]}
            else:
                role = "user" if msg["role"] == "user" else "model"
                contents.append({"role": role, "parts": [{"text": msg["content"]}]})

        payload: Dict = {
            "contents": contents,
            "generationConfig": {"temperature": temperature},
        }
        if system_instruction:
            payload["systemInstruction"] = system_instruction
        return payload

    async def _call_gemini(self, model: str, messages: List[Dict[str, str]], temperature: float) -> str:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={settings.GEMINI_API_KEY}"
        )
        payload = self._build_gemini_payload(messages, temperature)
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
        candidates = data.get("candidates", [])
        if candidates:
            return candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        return ""

    async def _stream_gemini(self, model: str, messages: List[Dict[str, str]], temperature: float) -> AsyncGenerator[str, None]:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:streamGenerateContent?key={settings.GEMINI_API_KEY}"
        )
        payload = self._build_gemini_payload(messages, temperature)

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                buffer = ""
                async for chunk in response.aiter_text():
                    buffer += chunk
                    while True:
                        trimmed = buffer.strip().lstrip("[").rstrip("]").lstrip(",").strip()
                        start = trimmed.find("{")
                        if start == -1:
                            break
                        depth, end = 0, -1
                        for i in range(start, len(trimmed)):
                            if trimmed[i] == "{":
                                depth += 1
                            elif trimmed[i] == "}":
                                depth -= 1
                                if depth == 0:
                                    end = i
                                    break
                        if end == -1:
                            break
                        try:
                            obj = json.loads(trimmed[start: end + 1])
                            text = (
                                obj.get("candidates", [{}])[0]
                                .get("content", {})
                                .get("parts", [{}])[0]
                                .get("text", "")
                            )
                            if text:
                                yield text
                        except Exception:
                            pass
                        buffer = trimmed[end + 1:]

    # ── Ollama ────────────────────────────────────────────────────────────────

    async def _call_ollama(self, messages: List[Dict[str, str]], temperature: float) -> str:
        url = f"{settings.OLLAMA_BASE_URL}/api/chat"
        payload = {
            "model": self.ollama_model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json().get("message", {}).get("content", "")

    async def _stream_ollama(self, messages: List[Dict[str, str]], temperature: float) -> AsyncGenerator[str, None]:
        url = f"{settings.OLLAMA_BASE_URL}/api/chat"
        payload = {
            "model": self.ollama_model,
            "messages": messages,
            "stream": True,
            "options": {"temperature": temperature},
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.strip():
                        try:
                            data = json.loads(line)
                            chunk = data.get("message", {}).get("content", "")
                            if chunk:
                                yield chunk
                        except Exception:
                            continue


llm_service = LLMService()

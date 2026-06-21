import json
import logging
from typing import AsyncGenerator, Dict, List, Optional
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        self.gemini_model = "gemini-2.5-flash"
        self.ollama_model = "llama3"

    async def generate_response(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
        """
        Generates a non-streaming response.
        """
        if settings.GEMINI_API_KEY:
            try:
                return await self._call_gemini(messages, temperature)
            except Exception as e:
                logger.error(f"Gemini API generation failed: {e}. Falling back to Ollama...")

        try:
            return await self._call_ollama(messages, temperature)
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}.")
            return (
                "⚠️ **Service Notice:** I was unable to connect to the Gemini API or a local Ollama instance. "
                "Please configure a valid `GEMINI_API_KEY` in your backend environment or start Ollama locally."
            )

    async def stream_response(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> AsyncGenerator[str, None]:
        """
        Streams response chunks.
        """
        if settings.GEMINI_API_KEY:
            try:
                async for chunk in self._stream_gemini(messages, temperature):
                    yield chunk
                return
            except Exception as e:
                logger.error(f"Gemini API streaming failed: {e}. Falling back to Ollama stream...")

        try:
            async for chunk in self._stream_ollama(messages, temperature):
                yield chunk
        except Exception as e:
            logger.error(f"Ollama streaming failed: {e}.")
            yield (
                "\n\n⚠️ **Service Notice:** Failed to stream from both Gemini and Ollama. "
                "Please check your API keys and local servers."
            )

    def _prepare_gemini_payload(self, messages: List[Dict[str, str]], temperature: float) -> Dict:
        contents = []
        system_instruction = None
        
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                system_instruction = {"parts": [{"text": content}]}
            else:
                gemini_role = "user" if role == "user" else "model"
                contents.append({
                    "role": gemini_role,
                    "parts": [{"text": content}]
                })
        
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature
            }
        }
        if system_instruction:
            payload["systemInstruction"] = system_instruction
            
        return payload

    async def _call_gemini(self, messages: List[Dict[str, str]], temperature: float) -> str:
        payload = self._prepare_gemini_payload(messages, temperature)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent?key={settings.GEMINI_API_KEY}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            res_data = response.json()
            
            # Parse response
            candidates = res_data.get("candidates", [])
            if candidates:
                text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                return text
            return ""

    async def _stream_gemini(self, messages: List[Dict[str, str]], temperature: float) -> AsyncGenerator[str, None]:
        payload = self._prepare_gemini_payload(messages, temperature)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:streamGenerateContent?key={settings.GEMINI_API_KEY}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                
                # Gemini stream returns JSON array/chunks
                buffer = ""
                async for chunk in response.aiter_text():
                    buffer += chunk
                    # Try to parse buffer as JSON chunks or clean delimiters
                    while True:
                        # Find matching square brackets or JSON segments
                        # Simple parse: Gemini sends stream chunks containing individual structures.
                        # For SSE-like streaming, let's parse using json.loads or simple regex.
                        # The stream text is a JSON array: [ { ... }, { ... } ]
                        # We can clean characters and split on JSON blocks or process line by line.
                        # A robust way is scanning for valid json objects.
                        try:
                            # If we can parse the buffer as a single JSON object (e.g. streaming chunks can be line-delimited in some networks, or array elements)
                            # Let's clean bracket boundaries:
                            trimmed = buffer.strip()
                            if trimmed.startswith("["):
                                trimmed = trimmed[1:]
                            if trimmed.endswith("]"):
                                trimmed = trimmed[:-1]
                            
                            # Clean leading commas
                            if trimmed.startswith(","):
                                trimmed = trimmed[1:]
                                
                            # If it's a complete candidate
                            # Let's write a simple extraction that finds objects between curly braces.
                            # Since JSON responses are standard, we search for the first '{' and its matching '}'
                            start = trimmed.find("{")
                            if start == -1:
                                break
                                
                            depth = 0
                            end = -1
                            for i in range(start, len(trimmed)):
                                if trimmed[i] == "{":
                                    depth += 1
                                elif trimmed[i] == "}":
                                    depth -= 1
                                    if depth == 0:
                                        end = i
                                        break
                            
                            if end != -1:
                                obj_str = trimmed[start:end+1]
                                obj = json.loads(obj_str)
                                text = obj.get("candidates", [])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                                if text:
                                    yield text
                                # Remove parsed block from buffer
                                # Map back index to buffer
                                buffer = trimmed[end+1:]
                            else:
                                break
                        except Exception:
                            # Incomplete chunk or parse error, wait for more data
                            break

    async def _call_ollama(self, messages: List[Dict[str, str]], temperature: float) -> str:
        # Convert messages to Ollama format (standard system, user, assistant)
        url = f"{settings.OLLAMA_BASE_URL}/api/chat"
        payload = {
            "model": self.ollama_model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            res_data = response.json()
            return res_data.get("message", {}).get("content", "")

    async def _stream_ollama(self, messages: List[Dict[str, str]], temperature: float) -> AsyncGenerator[str, None]:
        url = f"{settings.OLLAMA_BASE_URL}/api/chat"
        payload = {
            "model": self.ollama_model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": temperature
            }
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
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

"""
Ollama API Client for local LLM inference.
Communicates with a locally running Ollama instance.
"""

import requests
import json
from typing import Optional


class OllamaClient:
    """Client for interacting with a local Ollama instance."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "mistral"):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def is_available(self) -> bool:
        """Check if Ollama is running and accessible."""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return resp.status_code == 200
        except requests.ConnectionError:
            return False

    def list_models(self) -> list[str]:
        """List all locally available models."""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []

    def generate(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.8,
        top_p: float = 0.9,
        top_k: int = 40,
        repeat_penalty: float = 1.15,
        num_predict: int = 4096,
        timeout: int = 300,
    ) -> str:
        """
        Generate a completion using the local model.

        Parameters tuned for humanization:
        - temperature: Controls randomness (higher = more varied/human)
        - top_p: Nucleus sampling for natural word selection
        - top_k: Limits vocabulary to top-k tokens
        - repeat_penalty: Penalizes repetitive patterns (AI tends to repeat)
        - num_predict: Max tokens to generate
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system,
            "stream": False,
            "options": {
                "temperature": temperature,
                "top_p": top_p,
                "top_k": top_k,
                "repeat_penalty": repeat_penalty,
                "num_predict": num_predict,
            },
        }

        try:
            resp = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "").strip()
        except requests.Timeout:
            raise TimeoutError(
                f"Ollama request timed out after {timeout}s. "
                "Try a smaller text or increase timeout."
            )
        except requests.ConnectionError:
            raise ConnectionError(
                "Cannot connect to Ollama. Make sure Ollama is running: "
                "https://ollama.com/download"
            )
        except Exception as e:
            raise RuntimeError(f"Ollama generation failed: {e}")

    def generate_stream(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.8,
        top_p: float = 0.9,
        top_k: int = 40,
        repeat_penalty: float = 1.15,
        num_predict: int = 4096,
    ):
        """Stream generation token by token (for real-time UI feedback)."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system,
            "stream": True,
            "options": {
                "temperature": temperature,
                "top_p": top_p,
                "top_k": top_k,
                "repeat_penalty": repeat_penalty,
                "num_predict": num_predict,
            },
        }

        try:
            with requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                stream=True,
                timeout=300,
            ) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if line:
                        chunk = json.loads(line)
                        token = chunk.get("response", "")
                        if token:
                            yield token
                        if chunk.get("done", False):
                            break
        except Exception as e:
            raise RuntimeError(f"Ollama streaming failed: {e}")

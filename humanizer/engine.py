# engine.py — main logic that ties everything together

import re
import time
from typing import Optional, Generator

from .ollama_client import OllamaClient
from .prompts import get_system_prompt, build_rewrite_prompt
from .postprocessor import postprocess


# keep chunks under this so we don't time out on big inputs
MAX_CHUNK_SIZE = 2000


class HumanizerEngine:

    def __init__(
        self,
        model: str = "mistral",
        ollama_url: str = "http://localhost:11434",
    ):
        self.client = OllamaClient(base_url=ollama_url, model=model)
        self.model = model

    def check_status(self) -> dict:
        available = self.client.is_available()
        models = self.client.list_models() if available else []
        model_ready = any(self.model in m for m in models)

        return {
            "ollama_running": available,
            "models_available": models,
            "selected_model": self.model,
            "model_ready": model_ready,
            "status": "ready" if (available and model_ready) else "not_ready",
            "message": self._status_message(available, model_ready, models),
        }

    def _status_message(self, available: bool, model_ready: bool, models: list) -> str:
        if not available:
            return (
                "Ollama is not running. Please install and start Ollama: "
                "https://ollama.com/download"
            )
        if not model_ready:
            return (
                f"Model '{self.model}' not found. "
                f"Run: ollama pull {self.model}\n"
                f"Available models: {', '.join(models) if models else 'none'}"
            )
        return f"Ready — using {self.model}"

    def set_model(self, model: str):
        self.model = model
        self.client.model = model

    def _split_into_chunks(self, text: str) -> list[str]:
        # break long text into paragraph-sized pieces
        if len(text) <= MAX_CHUNK_SIZE:
            return [text]

        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = ""

        for para in paragraphs:
            if len(current_chunk) + len(para) + 2 > MAX_CHUNK_SIZE:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                # If a single paragraph exceeds max, split on sentences
                if len(para) > MAX_CHUNK_SIZE:
                    sentences = re.split(r'(?<=[.!?])\s+', para)
                    sub_chunk = ""
                    for sent in sentences:
                        if len(sub_chunk) + len(sent) + 1 > MAX_CHUNK_SIZE:
                            if sub_chunk:
                                chunks.append(sub_chunk.strip())
                            sub_chunk = sent
                        else:
                            sub_chunk += (" " if sub_chunk else "") + sent
                    if sub_chunk:
                        current_chunk = sub_chunk
                    else:
                        current_chunk = ""
                else:
                    current_chunk = para
            else:
                current_chunk += ("\n\n" if current_chunk else "") + para

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks

    def _get_generation_params(self, tone: str) -> dict:
        # tuned for maximum humanness — higher temp + repeat penalty
        # pushes the LLM to be less predictable (= higher perplexity = harder to detect)
        base_params = {
            "temperature": 0.85,
            "top_p": 0.88,
            "top_k": 55,
            "repeat_penalty": 1.25,
        }

        if tone == "academic":
            base_params.update({
                "temperature": 0.78,
                "top_p": 0.85,
                "top_k": 50,
                "repeat_penalty": 1.22,
            })
        elif tone == "casual":
            base_params.update({
                "temperature": 0.95,
                "top_p": 0.92,
                "top_k": 65,
                "repeat_penalty": 1.28,
            })
        # "normal" uses base params

        return base_params

    def humanize(
        self,
        text: str,
        tone: str = "normal",
        intensity: float = 0.7,
    ) -> dict:
        # main entry point — takes text in, spits humanized text out
        start_time = time.time()

        # Validate
        text = text.strip()
        if not text:
            return {"error": "No text provided."}

        if len(text) < 20:
            return {"error": "Text is too short to humanize meaningfully."}

        # Get prompts and params
        system_prompt = get_system_prompt(tone)
        gen_params = self._get_generation_params(tone)

        # Split into chunks if needed
        chunks = self._split_into_chunks(text)

        # Process each chunk
        humanized_parts = []
        previous_context = ""

        for i, chunk in enumerate(chunks):
            user_prompt = build_rewrite_prompt(chunk, previous_context)

            try:
                result = self.client.generate(
                    prompt=user_prompt,
                    system=system_prompt,
                    **gen_params,
                )
            except Exception as e:
                return {"error": str(e)}

            # Post-process each chunk
            processed = postprocess(result, tone=tone, intensity=intensity)
            humanized_parts.append(processed)
            previous_context = processed

        # Combine all chunks
        final_text = "\n\n".join(humanized_parts)

        elapsed = round(time.time() - start_time, 2)

        return {
            "result": final_text,
            "original_length": len(text),
            "new_length": len(final_text),
            "chunks_processed": len(chunks),
            "time_taken": elapsed,
            "tone": tone,
            "model": self.model,
        }

    def humanize_stream(
        self,
        text: str,
        tone: str = "normal",
    ) -> Generator[str, None, None]:
        # streaming version — pushes tokens as they come in
        text = text.strip()
        if not text:
            yield "[Error: No text provided]"
            return

        system_prompt = get_system_prompt(tone)
        gen_params = self._get_generation_params(tone)
        user_prompt = build_rewrite_prompt(text)

        try:
            for token in self.client.generate_stream(
                prompt=user_prompt,
                system=system_prompt,
                temperature=gen_params["temperature"],
                top_p=gen_params["top_p"],
                top_k=gen_params["top_k"],
                repeat_penalty=gen_params["repeat_penalty"],
            ):
                yield token
        except Exception as e:
            yield f"\n[Error: {e}]"

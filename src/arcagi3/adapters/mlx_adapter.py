"""
MLX Local Model Adapter for ARC-AGI-3.

Runs Qwen models locally on Apple Silicon via mlx-lm.
Zero API cost. Requires macOS 15+ and Apple Silicon.

Usage:
    # In models.yml, add a config like:
    - name: "qwen3.5-35b-local"
      model_name: "mlx-community/Qwen3.5-35B-A3B-4bit"
      provider: "mlx"
      is_multimodal: false
      max_completion_tokens: 4096
      temperature: 0.7
      pricing:
        input: 0.0
        output: 0.0
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from arcagi3.adapters.provider import ProviderAdapter
from arcagi3.schemas import (
    Attempt,
    AttemptMetadata,
    Choice,
    CompletionTokensDetails,
    Cost,
    Message,
    Usage,
)
from arcagi3.utils.parsing import extract_json_from_response as parse_json

logger = logging.getLogger(__name__)


@dataclass
class MLXResponse:
    """Response wrapper for MLX local inference."""

    text: str
    prompt_tokens: int
    completion_tokens: int


class MlxAdapter(ProviderAdapter):
    """Local MLX inference adapter for Apple Silicon.

    Loads the model once at initialization and keeps it resident in
    unified memory across all calls. No API key required.
    """

    def init_client(self):
        """Load model and tokenizer into memory."""
        try:
            from mlx_lm import load
        except ImportError:
            raise ImportError(
                "mlx-lm is required for local MLX inference. "
                "Install with: uv sync --extra mlx"
            )

        model_name = self.model_config.model_name
        logger.info(f"Loading MLX model: {model_name} (this may take a moment)...")

        self._model, self._tokenizer = load(model_name)
        logger.info(f"MLX model loaded: {model_name}")
        return None  # No external client needed

    def make_prediction(
        self,
        prompt: str,
        task_id: Optional[str] = None,
        test_id: Optional[str] = None,
        pair_index: int = None,
    ) -> Attempt:
        """Make a prediction with the local MLX model."""
        start_time = datetime.now(timezone.utc)

        messages = [{"role": "user", "content": prompt}]
        response = self.call_provider(messages)

        end_time = datetime.now(timezone.utc)

        input_choices = [
            Choice(index=0, message=Message(role="user", content=prompt))
        ]
        response_choices = [
            Choice(
                index=1,
                message=Message(role="assistant", content=response.text),
            )
        ]

        metadata = AttemptMetadata(
            model=self.model_config.model_name,
            provider=self.model_config.provider,
            start_timestamp=start_time,
            end_timestamp=end_time,
            choices=input_choices + response_choices,
            kwargs=self.model_config.kwargs,
            usage=Usage(
                prompt_tokens=response.prompt_tokens,
                completion_tokens=response.completion_tokens,
                total_tokens=response.prompt_tokens + response.completion_tokens,
                completion_tokens_details=CompletionTokensDetails(
                    reasoning_tokens=0,
                    accepted_prediction_tokens=response.completion_tokens,
                    rejected_prediction_tokens=0,
                ),
            ),
            cost=Cost(
                prompt_cost=0.0,
                completion_cost=0.0,
                total_cost=0.0,
            ),
            task_id=task_id,
            pair_index=pair_index,
            test_id=test_id,
        )

        return Attempt(metadata=metadata, answer=response.text)

    def call_provider(self, messages: List[Dict[str, Any]]) -> MLXResponse:
        """Run local inference via mlx-lm."""
        from mlx_lm import generate

        chat_messages = self._convert_messages(messages)
        prompt = self._tokenizer.apply_chat_template(
            chat_messages, tokenize=False, add_generation_prompt=True
        )

        # Get generation params from config kwargs
        kwargs = self.model_config.kwargs
        max_tokens = kwargs.get(
            "max_completion_tokens", kwargs.get("max_tokens", 4096)
        )
        temperature = kwargs.get("temperature", 0.7)
        top_p = kwargs.get("top_p", 0.9)
        repetition_penalty = kwargs.get("repetition_penalty", None)

        generate_kwargs = {
            "max_tokens": max_tokens,
            "temp": temperature,
            "top_p": top_p,
        }
        if repetition_penalty is not None:
            generate_kwargs["repetition_penalty"] = repetition_penalty

        logger.debug(
            f"MLX generate: max_tokens={max_tokens}, temp={temperature}, top_p={top_p}"
        )

        response_text = generate(
            self._model,
            self._tokenizer,
            prompt=prompt,
            **generate_kwargs,
        )

        # Strip thinking tags if present (Qwen /think mode)
        response_text = self._strip_thinking_tags(response_text)

        # Count tokens
        prompt_tokens = len(self._tokenizer.encode(prompt))
        completion_tokens = len(self._tokenizer.encode(response_text))

        return MLXResponse(
            text=response_text,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

    def _convert_messages(
        self, messages: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """Convert framework message format to simple chat messages.

        The framework sends OpenAI-format messages with structured content
        blocks (text, image_url). Since MLX models are text-only, we extract
        text content and replace image blocks with placeholders.
        """
        converted = []
        for msg in messages:
            role = msg["role"]
            content = msg.get("content", "")

            if isinstance(content, str):
                converted.append({"role": role, "content": content})
            elif isinstance(content, list):
                text_parts = []
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            text_parts.append(block["text"])
                        elif block.get("type") in ("image_url", "image"):
                            text_parts.append(
                                "[Image frame provided as text grid above]"
                            )
                    elif isinstance(block, str):
                        text_parts.append(block)
                converted.append(
                    {"role": role, "content": "\n".join(text_parts)}
                )
            else:
                converted.append({"role": role, "content": str(content)})

        return converted

    def _strip_thinking_tags(self, text: str) -> str:
        """Strip Qwen thinking tags from output, keeping only the answer."""
        import re

        # Remove <think>...</think> blocks
        stripped = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
        return stripped.strip()

    def extract_json_from_response(self, input_response: str) -> List[List[int]]:
        """Extract JSON from response text using shared parser."""
        try:
            result = parse_json(input_response)
            if isinstance(result, dict) and "response" in result:
                return result["response"]
            return result
        except ValueError:
            return None

    def extract_usage(self, response: Any) -> tuple[int, int, int]:
        """Extract token usage from MLXResponse."""
        if isinstance(response, MLXResponse):
            return response.prompt_tokens, response.completion_tokens, 0
        return 0, 0, 0

    def extract_content(self, response: Any) -> str:
        """Extract text content from MLXResponse."""
        if isinstance(response, MLXResponse):
            return response.text
        return str(response)

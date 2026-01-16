import openai
from config import Config
import instructor
from typing import Optional, Type, TypeVar
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)

class LLMClient:
    """LLM client for interacting with OpenAI-compatible APIs (OpenAI, DeepSeek, Gemini) with Instructor integration"""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize LLM client with both raw and instructor clients"""
        self._api_key_override = api_key.strip() if api_key and api_key.strip() else None
        self._active_api_key = None
        self._api_base = Config.OPENAI_API_BASE

        resolved_key = self._resolve_api_key()
        self._api_base = self._resolve_api_base(resolved_key)
        self.model_name = self._resolve_model_name(resolved_key)

        # Detect if using Gemini API
        self.is_gemini = self._detect_gemini_api(self._api_base, self.model_name)

        # Detect if using newer OpenAI models that require max_completion_tokens
        self.use_max_completion_tokens = self._should_use_max_completion_tokens(self.model_name)

        self._init_clients(resolved_key)

        if self.is_gemini:
            print(f"LLMClient: Detected Gemini API - using model {self.model_name}")
        if self.use_max_completion_tokens:
            print(f"LLMClient: Using max_completion_tokens for model {self.model_name}")

    def _is_quota_error(self, message: str) -> bool:
        lowered = message.lower()
        return (
            "requires more credits" in lowered
            or "insufficient" in lowered
            or "can only afford" in lowered
            or "insufficient_quota" in lowered
            or "quota" in lowered
        )

    def _record_last_error(self, error: Exception) -> None:
        message = str(error)
        try:
            from models.shared_context import SharedContext

            context = SharedContext.get_instance()
            context.session_info["last_llm_error"] = message
            context.session_info["last_llm_error_is_quota"] = self._is_quota_error(message)
        except Exception:
            return

    def _get_session_api_key(self) -> Optional[str]:
        """Fetch per-session API key override if available."""
        try:
            from models.shared_context import SharedContext
            api_key = SharedContext.get_instance().session_info.get("api_key_override")
            if isinstance(api_key, str):
                api_key = api_key.strip()
                return api_key or None
        except Exception:
            return None
        return None

    def _resolve_api_key(self) -> Optional[str]:
        """Resolve API key with override precedence."""
        return self._api_key_override or self._get_session_api_key() or Config.OPENAI_API_KEY

    def _is_gemini_key(self, api_key: Optional[str]) -> bool:
        if not api_key:
            return False
        return api_key.strip().startswith("AIza")

    def _is_openrouter_key(self, api_key: Optional[str]) -> bool:
        if not api_key:
            return False
        return api_key.strip().startswith("sk-or-")

    def _resolve_api_base(self, api_key: Optional[str]) -> Optional[str]:
        if self._is_gemini_key(api_key):
            return "https://generativelanguage.googleapis.com/v1beta/openai"
        if self._is_openrouter_key(api_key):
            return "https://openrouter.ai/api/v1"
        return Config.OPENAI_API_BASE

    def _resolve_model_name(self, api_key: Optional[str]) -> str:
        model_name = Config.OPENAI_MODEL_NAME
        if self._is_gemini_key(api_key):
            if model_name.startswith("google/"):
                return model_name.split("/", 1)[1]
        if self._is_openrouter_key(api_key):
            if "/" not in model_name and model_name.startswith("gemini"):
                return f"google/{model_name}"
        return model_name

    def _init_clients(self, api_key: Optional[str]) -> None:
        client_kwargs = {"api_key": api_key}
        if self._api_base:
            client_kwargs["base_url"] = self._api_base

        self.raw_client = openai.OpenAI(**client_kwargs)
        self.instructor_client = instructor.from_openai(
            openai.OpenAI(**client_kwargs),
            mode=instructor.Mode.JSON
        )
        self._active_api_key = api_key

    def _ensure_clients(self) -> None:
        resolved_key = self._resolve_api_key()
        resolved_base = self._resolve_api_base(resolved_key)
        resolved_model = self._resolve_model_name(resolved_key)
        if resolved_key != self._active_api_key or resolved_base != self._api_base or resolved_model != self.model_name:
            self._api_base = resolved_base
            self.model_name = resolved_model
            self.is_gemini = self._detect_gemini_api(self._api_base, self.model_name)
            self.use_max_completion_tokens = self._should_use_max_completion_tokens(self.model_name)
            self._init_clients(resolved_key)

    def _detect_gemini_api(self, api_base: str, model_name: str) -> bool:
        """Detect if using Gemini API based on base URL or model name"""
        if not api_base and not model_name:
            return False

        # Check if base URL contains Gemini endpoint
        if api_base and "generativelanguage.googleapis.com" in api_base:
            return True

        # Check if model name starts with "gemini"
        if model_name and model_name.startswith("gemini"):
            return True

        return False

    def _should_use_max_completion_tokens(self, model_name: str) -> bool:
        """Detect if model requires max_completion_tokens instead of max_tokens

        OpenAI introduced max_completion_tokens in newer models (o1, GPT-4.5, GPT-5.x)
        to replace the old max_tokens parameter.
        """
        if not model_name:
            return False

        # Models that require max_completion_tokens
        new_models = [
            "o1",           # o1-preview, o1-mini
            "gpt-4.5",      # GPT-4.5
            "gpt-5.1",        # GPT-5.x
            "chatgpt-4o-latest"  # Latest ChatGPT
        ]

        model_lower = model_name.lower()
        return any(new_model in model_lower for new_model in new_models)
    
    def generate_response(self,
                         prompt: str,
                         system_prompt: str = None,
                         response_model: Optional[Type[T]] = None,
                         max_retries: int = 3) -> str | T:

        self._ensure_clients()
       
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        if response_model:
            # Use Instructor client for structured output
            try:
                # Build API call parameters
                call_params = {
                    "model": self.model_name,
                    "response_model": response_model,
                    "messages": messages,
                    "temperature": 0,
                    "max_retries": max_retries
                }

                # Use correct token limit parameter based on model
                if self.use_max_completion_tokens:
                    call_params["max_completion_tokens"] = Config.MAX_TOKENS_STRUCTURED
                else:
                    call_params["max_tokens"] = Config.MAX_TOKENS_STRUCTURED

                response = self.instructor_client.chat.completions.create(**call_params)
                return response
            except Exception as e:
                print(f"Instructor API call failed: {e}")
                self._record_last_error(e)
                return None  # Return None instead of error string
        else:
            # Use raw OpenAI client for plain text responses
            try:
                for attempt in range(max_retries):
                    try:
                        # Build API call parameters
                        call_params = {
                            "model": self.model_name,
                            "messages": messages,
                            "temperature": 0,
                            "timeout": Config.LLM_TIMEOUT  # Configurable timeout via LLM_TIMEOUT env var
                        }

                        # Use correct token limit parameter based on model
                        if self.use_max_completion_tokens:
                            call_params["max_completion_tokens"] = Config.MAX_TOKENS_TEXT
                        else:
                            call_params["max_tokens"] = Config.MAX_TOKENS_TEXT

                        response = self.raw_client.chat.completions.create(**call_params)

                        content = response.choices[0].message.content
                        if content is None or content.strip() == "":
                            raise ValueError("Empty response from LLM")

                        return content

                    except Exception as e:
                        print(f"LLM API call failed (attempt {attempt + 1}/{max_retries}): {e}")
                        self._record_last_error(e)
                        if attempt == max_retries - 1:
                            return f"API call failed after {max_retries} attempts: {e}"
                        continue

                return "API call failed: Maximum retries exceeded"

            except Exception as e:
                print(f"Plain text API call failed: {e}")
                self._record_last_error(e)
                return f"API call failed: {e}"



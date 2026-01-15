import openai
from config import Config
import instructor
from typing import Optional, Type, TypeVar
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)

class LLMClient:
    """LLM client for interacting with OpenAI-compatible APIs (OpenAI, DeepSeek, Gemini) with Instructor integration"""

    def __init__(self):
        """Initialize LLM client with both raw and instructor clients"""
        client_kwargs = {"api_key": Config.OPENAI_API_KEY}
        if Config.OPENAI_API_BASE:
            client_kwargs["base_url"] = Config.OPENAI_API_BASE

        # Detect if using Gemini API
        self.is_gemini = self._detect_gemini_api(Config.OPENAI_API_BASE, Config.OPENAI_MODEL_NAME)

        # Detect if using newer OpenAI models that require max_completion_tokens
        self.use_max_completion_tokens = self._should_use_max_completion_tokens(Config.OPENAI_MODEL_NAME)

        # Create raw OpenAI client for plain text responses
        self.raw_client = openai.OpenAI(**client_kwargs)

        # Create instructor-wrapped client for structured output
        # Use JSON mode for DeepSeek/Gemini compatibility (instead of TOOLS mode)
        self.instructor_client = instructor.from_openai(
            openai.OpenAI(**client_kwargs),
            mode=instructor.Mode.JSON
        )

        self.model_name = Config.OPENAI_MODEL_NAME

        if self.is_gemini:
            print(f"LLMClient: Detected Gemini API - using model {self.model_name}")
        if self.use_max_completion_tokens:
            print(f"LLMClient: Using max_completion_tokens for model {self.model_name}")

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
                        if attempt == max_retries - 1:
                            return f"API call failed after {max_retries} attempts: {e}"
                        continue

                return "API call failed: Maximum retries exceeded"

            except Exception as e:
                print(f"Plain text API call failed: {e}")
                return f"API call failed: {e}"



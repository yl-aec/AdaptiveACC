import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """System configuration class"""

    # OpenAI API configuration (unified for all LLM operations)
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "gpt-4o")
    OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")

    # Token limits for LLM responses
    MAX_TOKENS_STRUCTURED = int(os.getenv("MAX_TOKENS_STRUCTURED", "16384"))  # For structured output (Pydantic models)
    MAX_TOKENS_TEXT = int(os.getenv("MAX_TOKENS_TEXT", "4096"))  # For plain text output

    # LLM timeout configuration
    LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "90"))  # Timeout in seconds for LLM API calls

    # Embedding API configuration (can be same as main API or different)
    EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", os.getenv("OPENAI_API_KEY"))
    EMBEDDING_API_BASE = os.getenv("EMBEDDING_API_BASE", os.getenv("OPENAI_API_BASE"))
    EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "text-embedding-ada-002")

    # System configuration
    DEBUG = os.getenv("DEBUG", "True").lower() == "true"
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8000"))
    
    # File upload configuration
    MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", "314572800"))  # 300MB
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
    
    # Phoenix tracing configuration
    PHOENIX_API_KEY = os.getenv("PHOENIX_API_KEY")
    PHOENIX_ENDPOINT = os.getenv("PHOENIX_ENDPOINT", "https://app.phoenix.arize.com/v1/traces")
    PHOENIX_PROJECT_NAME = os.getenv("PHOENIX_PROJECT_NAME", "ACC")
    PHOENIX_ENABLED = os.getenv("PHOENIX_ENABLED", "true").lower() == "true"
    
    @classmethod
    def validate(cls):
        """Validate if configuration is complete"""
        if not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        # Create necessary directories
        os.makedirs(cls.UPLOAD_DIR, exist_ok=True)
        
        return True 

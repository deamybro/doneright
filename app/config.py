import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION", "us-west-2")

# Default model configuration
GEMINI_MODEL_ID = os.getenv("GEMINI_MODEL_ID", "gemini-3.6-flash")
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0")

def get_strands_model():
    """
    Initializes and returns the configured Strands model provider.
    Prefers Gemini if GEMINI_API_KEY is present, falls back to Bedrock if configured.
    """
    if GEMINI_API_KEY:
        try:
            from strands.models.gemini import GeminiModel
            return GeminiModel(
                client_args={"api_key": GEMINI_API_KEY},
                model_id=GEMINI_MODEL_ID,
                params={"temperature": 0.2}
            )
        except Exception as e:
            # If strands gemini wrapper needs alternative init
            raise RuntimeError(f"Failed to initialize Strands GeminiModel: {e}")
    elif AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
        try:
            from strands.models import BedrockModel
            return BedrockModel(
                model_id=BEDROCK_MODEL_ID,
                region_name=AWS_DEFAULT_REGION,
                temperature=0.2
            )
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Strands BedrockModel: {e}")
    else:
        raise ValueError(
            "No LLM credentials found. Please set GEMINI_API_KEY in .env "
            "or configure AWS Bedrock credentials."
        )

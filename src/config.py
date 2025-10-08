import os

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
AGENT_OPS_API_KEY = os.environ.get("AGENT_OPS_API_KEY")

LLM_MODEL = "llama-3.1-70b-versatile"
IMAGE_MODEL = "moondream"

SUPPORTED_EXTENSIONS = [
    ".pdf",
    ".txt",
    ".md",
    ".png",
    ".jpg",
    ".jpeg",
]
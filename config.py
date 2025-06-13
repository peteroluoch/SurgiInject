import os

class Config:
    def __init__(self):
        self.providers = {
            "groq": os.getenv("GROQ_API_KEY"),
            "mistral": os.getenv("MISTRAL_API_KEY"),
            "anthropic": os.getenv("ANTHROPIC_API_KEY")
        }
        self.fallback_order = ["groq", "mistral", "anthropic"]
        self.timeout = 15  # seconds
        self.model_map = {
            "groq": "llama3-70b-8192",
            "mistral": "open-mistral-7b",
            "anthropic": "claude-3-haiku-20240307"
        }

    def available_providers(self):
        return [p for p, key in self.providers.items() if key]

CONFIG = Config()

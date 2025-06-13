import requests
import time
from surgiinject.config import CONFIG
from surgiinject.metrics import track_metrics

class SurgiInject:
    def __init__(self):
        self.config = CONFIG

    def inject(self, prompt):
        for provider in self.config.fallback_order:
            if self.config.providers.get(provider):
                try:
                    print(f"🔁 Trying: {provider}")
                    output = self._attempt_provider(provider, prompt)
                    track_metrics(provider, success=True)
                    return output
                except Exception as e:
                    print(f"❌ {provider} failed: {e}")
                    track_metrics(provider, success=False)
        return self.fallback_final_message()

    def _attempt_provider(self, provider, prompt):
        if provider == "groq":
            return self._call_groq_api(prompt)
        if provider == "mistral":
            return self._call_mistral_api(prompt)
        if provider == "anthropic":
            return self._call_anthropic_api(prompt)
        raise ValueError(f"Unknown provider: {provider}")

    def _call_groq_api(self, prompt):
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.config.providers['groq']}",
                "Content-Type": "application/json"
            },
            json={
                "model": self.config.model_map["groq"],
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 1024
            },
            timeout=self.config.timeout
        )
        return r.json()["choices"][0]["message"]["content"]

    def _call_mistral_api(self, prompt):
        r = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.config.providers['mistral']}",
                "Content-Type": "application/json"
            },
            json={
                "model": self.config.model_map["mistral"],
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 1024
            },
            timeout=self.config.timeout
        )
        return r.json()["choices"][0]["message"]["content"]

    def _call_anthropic_api(self, prompt):
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": self.config.providers["anthropic"],
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            },
            json={
                "model": self.config.model_map["anthropic"],
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 1024
            },
            timeout=self.config.timeout
        )
        return r.json()["content"][0]["text"]

    def fallback_final_message(self):
        return "🛑 All providers failed. Please check API keys or try again later."

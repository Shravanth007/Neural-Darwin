from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

@dataclass
class GroqPool:
    model: str = "llama-3.1-8b-instant"
    api_key_env: str = "GROQ_API_KEY"

    def _read_dotenv_value(self, key: str) -> str | None:
        env_path = Path(__file__).resolve().parents[1] / ".env"
        if not env_path.exists():
            return None

        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            k, v = line.split("=", 1)
            if k.strip() == key:
                return v.strip().strip('"').strip("'")

        return None

    def api_key(self) -> str | None:
        return os.getenv(self.api_key_env) or self._read_dotenv_value(self.api_key_env)

    def available(self) -> bool:
        return bool(self.api_key())

    def create_payload(self, prompt: str) -> dict[str, object]:
        return {
            "model": self.model,
            "messages": [{"role": "system", "content": prompt}],
            "temperature": 0.7,
        }

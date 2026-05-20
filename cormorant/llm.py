"""Gemini API client with rate limiting, retry logic, and call budget tracking."""

from __future__ import annotations

import json
import time
import logging
from collections import deque
from datetime import date, datetime
from pathlib import Path

from google import genai

# Late import to avoid circular dependency if possible, but count_tokens is utility
from cormorant.memory import count_tokens

logger = logging.getLogger(__name__)

MODELS = {
    "lite": {
        "name": "gemini-2.5-flash-lite",
        "rpm": 15,
        "rpd": 1500,
    },
    "gemma": {
        "name": "gemma-4-31b-it",
        "rpm": 15,
        "rpd": 1500,
    },
    "flash": {
        "name": "gemini-3.1-flash-lite",
        "rpm": 15,
        "rpd": 500,
    },
    "flash_fallback": {
        "name": "gemini-2.5-flash",
        "rpm": 15,
        "rpd": 500,
    },
}

# Call tracking (no hard limit enforced)


class RateGate:
    """Sliding-window RPM self-throttle."""

    def __init__(self, rpm: int) -> None:
        self.rpm = rpm
        self.calls: deque[float] = deque()

    def wait_if_needed(self) -> None:
        now = time.time()
        while self.calls and self.calls[0] < now - 60:
            self.calls.popleft()
        if len(self.calls) >= self.rpm:
            sleep_for = 60 - (now - self.calls[0]) + 0.5
            logger.info(f"Self-throttle: sleeping {sleep_for:.1f}s")
            time.sleep(sleep_for)
        self.calls.append(time.time())


class QuotaExceededError(Exception):
    pass


class LLMClient:
    def __init__(self, api_key: str, project_dir: Path | None = None) -> None:
        self._api_key = api_key
        self._client = genai.Client(api_key=api_key)
        self.project_dir = project_dir
        self.flash_gate = RateGate(rpm=MODELS["flash"]["rpm"])
        self.gemma_gate = RateGate(rpm=MODELS["gemma"]["rpm"])
        self.lite_gate = RateGate(rpm=MODELS["lite"]["rpm"])
        self._daily_usage: dict[str, int] = self._load_daily_usage()

    # ── daily usage persistence ──────────────────────────────────────────

    def _usage_path(self) -> Path:
        base = self.project_dir if self.project_dir else Path.home() / ".cormorant"
        base.mkdir(parents=True, exist_ok=True)
        return base / "quota.log"

    def _load_daily_usage(self) -> dict[str, int]:
        today = str(date.today())
        path = self._usage_path()
        if not path.exists():
            return {"date": today, "flash": 0, "gemma": 0, "lite": 0}
        counts: dict[str, int] = {"date": today, "flash": 0, "gemma": 0, "lite": 0}
        try:
            for line in path.read_text().splitlines():
                if not line.strip():
                    continue
                parts = line.split()
                if len(parts) < 3:
                    continue
                log_date = parts[0][:10]
                if log_date != today:
                    continue
                model_key = parts[1]
                if model_key in ("flash", "gemma", "lite"):
                    counts[model_key] = counts.get(model_key, 0) + 1
        except Exception:
            pass
        return counts

    def _log_call(
        self,
        model_key: str,
        call_label: str,
        tokens_in: int,
        tokens_out: int,
        status: str,
    ) -> None:
        ts = datetime.now().isoformat(timespec="seconds")
        line = f"{ts}  {model_key}  {call_label}  in={tokens_in}  out={tokens_out}  {status}\n"
        path = self._usage_path()
        with path.open("a") as f:
            f.write(line)

    def flash_calls_used(self) -> int:
        return self._daily_usage.get("flash", 0)

    def gemma_calls_used(self) -> int:
        return self._daily_usage.get("gemma", 0)

    def lite_calls_used(self) -> int:
        return self._daily_usage.get("lite", 0)

    # ── core call helpers ────────────────────────────────────────────────

    def _generate(self, model_name: str, prompt: str) -> str:
        from google.genai import types
        config = types.GenerateContentConfig(
            stop_sequences=["User:", "user:", "Cormorant:", "model:", "**Cormorant:**"],
            temperature=0.7
        )
        response = self._client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=config
        )
        text = response.text.strip()
        # Manual fail-safe truncation
        for stop in ["User:", "user:", "Cormorant:", "model:", "**Cormorant:**"]:
            if stop in text:
                text = text.split(stop)[0].strip()
        return text

    # ── public call API ──────────────────────────────────────────────────

    def call_flash(
        self,
        prompt: str,
        call_label: str = "unknown",
        schema: dict | None = None,
        max_retries: int = 2,
    ) -> str:
        model_name = MODELS["flash"]["name"]
        attempt = 0
        current_prompt = prompt

        while True:
            self.flash_gate.wait_if_needed()
            try:
                text = self._generate(model_name, current_prompt)
                tokens_in = count_tokens(prompt)
                tokens_out = count_tokens(text)
                self._log_call("flash", call_label, tokens_in, tokens_out, "ok")
                self._daily_usage["flash"] = self._daily_usage.get("flash", 0) + 1

                if schema is not None:
                    import jsonschema
                    try:
                        # Find the JSON object
                        start = text.find("{")
                        if start >= 0:
                            parsed = json.loads(text[start:])
                            jsonschema.validate(parsed, schema)
                    except (json.JSONDecodeError, jsonschema.ValidationError) as e:
                        if attempt < max_retries:
                            attempt += 1
                            logger.warning(f"Schema validation failed, retrying {attempt}/{max_retries}: {e}")
                            current_prompt = prompt + f"\n\nIMPORTANT: Your previous output failed validation. Please ensure you follow this JSON schema exactly: {json.dumps(schema)}"
                            continue
                        raise
                return text

            except Exception as e:
                err_str = str(e).lower()
                if "500" in err_str or "internal" in err_str:
                    if attempt < max_retries:
                        attempt += 1
                        logger.warning(f"Internal error (500), retrying {attempt}/{max_retries}...")
                        time.sleep(2)
                        continue
                if "quota" in err_str or "429" in err_str or "resource_exhausted" in err_str:
                    if "daily" in err_str or ("resource_exhausted" in err_str and "daily" not in err_str.lower()):
                        # Check if it's truly daily quota vs per-minute rate limit
                        if "per_day" in err_str or "daily" in err_str:
                            self._log_call("flash", call_label, 0, 0, "quota_exceeded")
                            raise QuotaExceededError(str(e)) from e
                    self._log_call("flash", call_label, 0, 0, "rate_limited_60s")
                    logger.info("Rate limited. Sleeping 60s.")
                    time.sleep(60)
                    continue
                raise

    def call_gemma(
        self,
        prompt: str,
        call_label: str = "gemma",
        max_retries: int = 3,
    ) -> str:
        model_name = MODELS["gemma"]["name"]
        attempt = 0

        while True:
            self.gemma_gate.wait_if_needed()
            try:
                text = self._generate(model_name, prompt)
                tokens_in = count_tokens(prompt)
                tokens_out = count_tokens(text)
                self._log_call("gemma", call_label, tokens_in, tokens_out, "ok")
                self._daily_usage["gemma"] = self._daily_usage.get("gemma", 0) + 1
                return text

            except Exception as e:
                err_str = str(e).lower()
                if "500" in err_str or "internal" in err_str:
                    if attempt < max_retries:
                        attempt += 1
                        logger.warning(f"Gemma Internal error (500), retrying {attempt}/{max_retries}...")
                        time.sleep(2)
                        continue
                if "quota" in err_str or "429" in err_str or "resource_exhausted" in err_str:
                    if "per_day" in err_str or "daily" in err_str:
                        self._log_call("gemma", call_label, 0, 0, "quota_exceeded")
                        raise QuotaExceededError(str(e)) from e
                    self._log_call("gemma", call_label, 0, 0, "rate_limited_60s")
                    logger.info("Rate limited on Gemma. Sleeping 60s.")
                    time.sleep(60)
                    continue
                raise

    def _generate_chat(self, model_key: str, history: list[dict], contents: list) -> str:
        from google.genai import types
        config = types.GenerateContentConfig(
            stop_sequences=["User:", "user:", "Cormorant:", "model:", "**Cormorant:**"],
            temperature=0.7
        )
        response = self._client.models.generate_content(
            model=MODELS[model_key]["name"],
            contents=contents,
            config=config
        )
        text = response.text.strip()
        for stop in ["User:", "user:", "Cormorant:", "model:"]:
            if stop in text:
                text = text.split(stop)[0].strip()
        return text

    def call_flash_chat(
        self,
        history: list[dict[str, str]],
        call_label: str = "chat",
        max_retries: int = 3,
    ) -> str:
        """Multi-turn chat using flash."""
        attempt = 0
        contents = []
        for msg in history:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})

        while True:
            self.flash_gate.wait_if_needed()
            try:
                text = self._generate_chat("flash", history, contents)
                self._log_call("flash", call_label, sum(len(m["content"]) // 4 for m in history), len(text) // 4, "ok")
                self._daily_usage["flash"] = self._daily_usage.get("flash", 0) + 1
                return text
            except Exception as e:
                err_str = str(e).lower()
                if "500" in err_str or "internal" in err_str:
                    if attempt < max_retries:
                        attempt += 1
                        logger.warning(f"Flash Chat Internal error (500), retrying {attempt}/{max_retries}...")
                        time.sleep(2)
                        continue
                if "quota" in err_str or "429" in err_str or "resource_exhausted" in err_str:
                    if "per_day" in err_str or "daily" in err_str:
                        raise QuotaExceededError(str(e)) from e
                    logger.info("Rate limited. Sleeping 60s.")
                    time.sleep(60)
                    continue
                raise

    def call_flash_fallback_chat(
        self,
        history: list[dict[str, str]],
        call_label: str = "chat_fallback",
        max_retries: int = 3,
    ) -> str:
        """Multi-turn chat using the 2.5 Flash fallback model."""
        attempt = 0
        contents = []
        for msg in history:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})

        while True:
            self.flash_gate.wait_if_needed()
            try:
                text = self._generate_chat("flash_fallback", history, contents)
                self._log_call("flash_fallback", call_label, sum(len(m["content"]) // 4 for m in history), len(text) // 4, "ok")
                self._daily_usage["flash"] = self._daily_usage.get("flash", 0) + 1
                return text
            except Exception as e:
                err_str = str(e).lower()
                if "500" in err_str or "internal" in err_str:
                    if attempt < max_retries:
                        attempt += 1
                        logger.warning(f"Fallback Internal error (500), retrying {attempt}/{max_retries}...")
                        time.sleep(2)
                        continue
                if "quota" in err_str or "429" in err_str or "resource_exhausted" in err_str:
                    if "per_day" in err_str or "daily" in err_str:
                        raise QuotaExceededError(str(e)) from e
                    logger.info("Rate limited on fallback. Sleeping 60s.")
                    time.sleep(60)
                    continue
                raise

    def call_gemma_chat(
        self,
        history: list[dict[str, str]],
        call_label: str = "gemma_chat",
        max_retries: int = 3,
    ) -> str:
        """Multi-turn chat using Gemma."""
        attempt = 0
        contents = []
        for msg in history:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})

        while True:
            self.gemma_gate.wait_if_needed()
            try:
                text = self._generate_chat("gemma", history, contents)
                self._log_call("gemma", call_label, sum(len(m["content"]) // 4 for m in history), len(text) // 4, "ok")
                self._daily_usage["gemma"] = self._daily_usage.get("gemma", 0) + 1
                return text
            except Exception as e:
                err_str = str(e).lower()
                if "500" in err_str or "internal" in err_str:
                    if attempt < max_retries:
                        attempt += 1
                        logger.warning(f"Gemma Chat Internal error (500), retrying {attempt}/{max_retries}...")
                        time.sleep(2)
                        continue
                if "quota" in err_str or "429" in err_str or "resource_exhausted" in err_str:
                    if "per_day" in err_str or "daily" in err_str:
                        raise QuotaExceededError(str(e)) from e
                    logger.info("Rate limited on Gemma. Sleeping 60s.")
                    time.sleep(60)
                    continue
                raise

    def call_lite_chat(
        self,
        history: list[dict[str, str]],
        call_label: str = "lite_chat",
        max_retries: int = 3,
    ) -> str:
        """Multi-turn chat using Gemini 2.5 Flash Lite."""
        attempt = 0
        contents = []
        for msg in history:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})

        while True:
            self.lite_gate.wait_if_needed()
            try:
                text = self._generate_chat("lite", history, contents)
                self._log_call("lite", call_label, sum(len(m["content"]) // 4 for m in history), len(text) // 4, "ok")
                self._daily_usage["lite"] = self._daily_usage.get("lite", 0) + 1
                return text
            except Exception as e:
                err_str = str(e).lower()
                if "500" in err_str or "internal" in err_str:
                    if attempt < max_retries:
                        attempt += 1
                        logger.warning(f"Lite Chat Internal error (500), retrying {attempt}/{max_retries}...")
                        time.sleep(2)
                        continue
                if "quota" in err_str or "429" in err_str or "resource_exhausted" in err_str:
                    if "per_day" in err_str or "daily" in err_str:
                        raise QuotaExceededError(str(e)) from e
                    logger.info("Rate limited on Lite. Sleeping 60s.")
                    time.sleep(60)
                    continue
                raise


# ── helpers ──────────────────────────────────────────────────────────────────

def _strip_code_fences(text: str) -> str:
    """Robustly remove markdown code fences, handling language tags and empty lines."""
    text = text.strip()
    if not text.startswith("```"):
        return text

    lines = text.splitlines()
    if not lines:
        return text

    # Remove starting fence (e.g., ```json or ```)
    start_idx = 1
    # Remove ending fence (e.g., ```)
    end_idx = len(lines)
    for i in range(len(lines) - 1, 0, -1):
        if lines[i].strip() == "```":
            end_idx = i
            break
    
    return "\n".join(lines[start_idx:end_idx]).strip()


def _save_validation_failure(project_dir: Path | None, label: str, text: str) -> None:
    base = (project_dir / "cache" / "validation_failures") if project_dir else Path.home() / ".cormorant" / "validation_failures"
    base.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    (base / f"{label}_{ts}.txt").write_text(text)

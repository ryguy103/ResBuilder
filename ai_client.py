"""
ai_client.py - Multi-provider AI abstraction for ResBuilder
Supports Anthropic (Claude), OpenAI (GPT), and Google (Gemini).
SDKs are installed on-demand when a provider is selected.
"""

import os
import sys
import subprocess
import importlib
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


def _env_file() -> Path:
    """Same rules as core.BASE_PATH: writable data dir when RESBUILDER_DATA_DIR is set."""
    data = os.environ.get("RESBUILDER_DATA_DIR", "").strip()
    if data:
        p = Path(data).expanduser().resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p / ".env"
    return Path(__file__).parent.resolve() / ".env"


load_dotenv(_env_file())


PROVIDERS = {
    "anthropic": {
        "name": "Anthropic (Claude)",
        "sdk_package": "anthropic",
        "sdk_import": "anthropic",
        "env_key": "ANTHROPIC_API_KEY",
        "default_model": "claude-sonnet-4-20250514",
        "signup_url": "https://console.anthropic.com/",
        "description": "Claude by Anthropic. Great at following detailed instructions and generating nuanced content.",
    },
    "openai": {
        "name": "OpenAI (GPT)",
        "sdk_package": "openai",
        "sdk_import": "openai",
        "env_key": "OPENAI_API_KEY",
        "default_model": "gpt-4o",
        "signup_url": "https://platform.openai.com/api-keys",
        "description": "GPT models by OpenAI. Widely used with broad capabilities.",
    },
    "google": {
        "name": "Google (Gemini)",
        "sdk_package": "google-generativeai",
        "sdk_import": "google.generativeai",
        "env_key": "GOOGLE_API_KEY",
        "default_model": "gemini-2.0-flash",
        "signup_url": "https://aistudio.google.com/apikey",
        "description": "Gemini by Google. Fast and capable with a generous free tier.",
    },
}


# ---------------------------------------------------------------------------
# .env helpers
# ---------------------------------------------------------------------------

def read_env() -> dict:
    """Read the .env file into a dictionary, ignoring comments and blanks."""
    env = {}
    path = _env_file()
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                env[key.strip()] = value.strip()
    return env


def write_env(key: str, value: str) -> None:
    """Set a single key in the .env file, preserving all other content."""
    path = _env_file()
    lines: list[str] = []
    found = False
    if path.exists():
        for line in path.read_text().splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                k, _, _ = stripped.partition("=")
                if k.strip() == key:
                    lines.append(f"{key}={value}")
                    found = True
                    continue
            lines.append(line)
    if not found:
        lines.append(f"{key}={value}")
    path.write_text("\n".join(lines) + "\n")
    os.environ[key] = value


# ---------------------------------------------------------------------------
# Provider detection & configuration
# ---------------------------------------------------------------------------

def get_active_provider() -> Optional[str]:
    """Return the currently configured provider id, or None."""
    provider_id = os.environ.get("AI_PROVIDER", "").strip().lower()
    if provider_id in PROVIDERS:
        return provider_id
    for pid, cfg in PROVIDERS.items():
        if os.environ.get(cfg["env_key"]):
            return pid
    return None


def set_provider(provider_id: str) -> None:
    """Persist the chosen provider to .env and environment."""
    if provider_id not in PROVIDERS:
        raise ValueError(f"Unknown provider: {provider_id}")
    write_env("AI_PROVIDER", provider_id)


def get_api_key(provider_id: Optional[str] = None) -> str:
    """Get the API key for the given (or active) provider."""
    provider_id = provider_id or get_active_provider()
    if not provider_id:
        raise ValueError("No AI provider configured. Visit /setup to get started.")
    cfg = PROVIDERS[provider_id]
    key = os.environ.get(cfg["env_key"], "")
    if not key:
        raise ValueError(
            f"{cfg['env_key']} not set. Get your key at {cfg['signup_url']}"
        )
    return key


def is_provider_ready(provider_id: Optional[str] = None) -> bool:
    """True when a provider has both an SDK and an API key available."""
    provider_id = provider_id or get_active_provider()
    if not provider_id:
        return False
    if not is_sdk_installed(provider_id):
        return False
    try:
        get_api_key(provider_id)
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# SDK management
# ---------------------------------------------------------------------------

def is_sdk_installed(provider_id: str) -> bool:
    """Check whether the SDK for a provider is importable."""
    cfg = PROVIDERS.get(provider_id)
    if not cfg:
        return False
    try:
        importlib.import_module(cfg["sdk_import"])
        return True
    except ImportError:
        return False


def install_sdk(provider_id: str) -> dict:
    """pip-install the SDK for a provider. Returns {success, output}."""
    cfg = PROVIDERS.get(provider_id)
    if not cfg:
        return {"success": False, "output": f"Unknown provider: {provider_id}"}
    package = cfg["sdk_package"]
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", package],
            capture_output=True, text=True, timeout=120,
        )
        ok = result.returncode == 0
        if ok:
            importlib.invalidate_caches()
        return {"success": ok, "output": result.stdout if ok else result.stderr}
    except subprocess.TimeoutExpired:
        return {"success": False, "output": "Installation timed out (120 s)."}
    except Exception as e:
        return {"success": False, "output": str(e)}


# ---------------------------------------------------------------------------
# Text generation
# ---------------------------------------------------------------------------

def generate_text(
    prompt: str,
    max_tokens: int = 2500,
    provider_id: Optional[str] = None,
) -> str:
    """Generate text using the active (or specified) AI provider."""
    provider_id = provider_id or get_active_provider()
    if not provider_id:
        raise ValueError("No AI provider configured. Visit /setup to get started.")

    cfg = PROVIDERS[provider_id]
    api_key = get_api_key(provider_id)
    model = cfg["default_model"]

    if provider_id == "anthropic":
        from anthropic import Anthropic

        client = Anthropic(api_key=api_key)
        resp = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text.strip()

    if provider_id == "openai":
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content.strip()

    if provider_id == "google":
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        gmodel = genai.GenerativeModel(model)
        resp = gmodel.generate_content(prompt)
        return resp.text.strip()

    raise ValueError(f"Unsupported provider: {provider_id}")


def test_connection(provider_id: Optional[str] = None) -> dict:
    """Quick smoke-test. Returns {success, message}."""
    provider_id = provider_id or get_active_provider()
    if not provider_id:
        return {"success": False, "message": "No provider configured."}
    if not is_sdk_installed(provider_id):
        return {
            "success": False,
            "message": f"SDK not installed for {PROVIDERS[provider_id]['name']}.",
        }
    try:
        result = generate_text(
            "Respond with exactly one word: OK",
            max_tokens=10,
            provider_id=provider_id,
        )
        return {
            "success": True,
            "message": f"Connected to {PROVIDERS[provider_id]['name']}.",
        }
    except Exception as e:
        return {"success": False, "message": str(e)}

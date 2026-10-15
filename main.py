import os
from pathlib import Path

import yaml
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS: lets the grader's web page call your API from the browser
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Layer 1: hardcoded defaults
DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}

ALIASES = {"num_workers": "workers"}   # NUM_WORKERS -> workers
TRUE_WORDS = {"true", "1", "yes", "on"}


def clean_key(key: str) -> str:
    key = key.strip().lower()
    return ALIASES.get(key, key)


def coerce(key, value):
    """Turn raw values into the right type."""
    if key in ("port", "workers"):
        return int(value)
    if key == "debug":
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in TRUE_WORDS
    return str(value)


def load_yaml():
    path = Path(__file__).parent / "config.development.yaml"
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text()) or {}
    return {clean_key(k): v for k, v in data.items()}


def load_dotenv():
    path = Path(__file__).parent / ".env"
    result = {}
    if not path.exists():
        return result
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        if k.upper().startswith("APP_"):
            k = k[4:]
        result[clean_key(k)] = v.strip().strip('"').strip("'")
    return result


def load_os_env():
    result = {}
    for k, v in os.environ.items():
        if k.startswith("APP_"):
            result[clean_key(k[4:])] = v
    return result


@app.get("/effective-config")
def effective_config(set: list[str] = Query(default=[])):
    config = dict(DEFAULTS)            # 1. defaults
    config.update(load_yaml())         # 2. yaml
    config.update(load_dotenv())       # 3. .env
    config.update(load_os_env())       # 4. OS env

    for item in set:                   # 5. CLI overrides (?set=key=value)
        if "=" in item:
            k, v = item.split("=", 1)
            config[clean_key(k)] = v

    final = {k: coerce(k, v) for k, v in config.items()}
    final["api_key"] = "****"          # never leak the secret
    return final

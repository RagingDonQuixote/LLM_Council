"""Configuration for the LLM Council."""

import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# OpenRouter API key
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Config file path
CONFIG_FILE = "config.json"

# Default configuration - Best free thinking models from OpenRouter
DEFAULT_CONFIG = {
    "council_models": [
        "xiaomi/mimo-v2-flash:free",           # Xiaomi free thinking model
        "tngtech/deepseek-r1t2-chimera:free",  # TNG free deep reasoning
        "nex-agi/deepseek-v3.1-nex-n1:free",   # Nex AGI free advanced
        "z-ai/glm-4.5-air:free",               # GLM free with reasoning
        "nvidia/nemotron-nano-12b-v2-vl:free", # NVIDIA free vision+language
    ],
    "chairman_model": "z-ai/glm-4.5-air:free",
    "consensus_strategy": "borda",
    "response_timeout": 60,  # Default timeout in seconds
    "substitute_models": {},
    "model_personalities": {
        "xiaomi/mimo-v2-flash:free": "Fast multimodal reasoning",
        "tngtech/deepseek-r1t2-chimera:free": "Deep analytical reasoning",
        "nex-agi/deepseek-v3.1-nex-n1:free": "Advanced logical reasoning",
        "z-ai/glm-4.5-air:free": "Balanced reasoning with insights",
        "nvidia/nemotron-nano-12b-v2-vl:free": "Vision-enhanced reasoning"
    }
}

# OpenRouter API endpoint
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Data directory for conversation storage
DATA_DIR = "data/conversations"
DB_PATH = "D:/DB_LLM_Council/council.db"

def load_config():
    """Load configuration from file or return defaults."""
    if Path(CONFIG_FILE).exists():
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return DEFAULT_CONFIG.copy()

def save_config(config):
    """Save configuration to file."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

# Load current config
_current_config = load_config()

def get_config():
    """Get current configuration."""
    global _current_config
    return _current_config

def update_config(new_config):
    """Update configuration."""
    global _current_config
    
    # Ensure council_models is within 1-6 range
    if "council_models" in new_config:
        models = new_config["council_models"]
        if len(models) < 1:
            new_config["council_models"] = models[:1] if models else [DEFAULT_CONFIG["council_models"][0]]
        elif len(models) > 6:
            new_config["council_models"] = models[:6]
            
    _current_config = new_config
    save_config(_current_config)

# Backward compatibility
COUNCIL_MODELS = _current_config.get("council_models", DEFAULT_CONFIG["council_models"])
CHAIRMAN_MODEL = _current_config.get("chairman_model", DEFAULT_CONFIG["chairman_model"])

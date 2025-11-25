import yaml
import os
import logging
from typing import Any, Dict

# Auto-install jsonschema if missing
try:
    from jsonschema import validate, ValidationError
except ImportError:
    import sys
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "jsonschema"])
    from jsonschema import validate, ValidationError

CONFIG_SCHEMA = {
    "type": "object",
    "required": ["version", "logging", "resources", "rate_limiting"],
    "properties": {
        "version": {"type": "string"},
        "logging": {
            "type": "object",
            "required": ["level"],
            "properties": {
                "level": {"enum": ["DEBUG", "INFO", "WARNING", "ERROR"]},
                "json_format": {"type": "boolean"}
            }
        },
        "resources": {
            "type": "object",
            "properties": {
                "max_workers_global": {"type": "integer", "minimum": 1},
                "auto_tune": {"type": "boolean"}
            }
        },
        "rate_limiting": {
            "type": "object",
            "required": ["global_rpm"],
            "properties": {
                "global_rpm": {"type": "integer", "minimum": 1},
                "adaptive": {"type": "boolean"}
            }
        }
    }
}

class ConfigLoader:
    _instance = None
    _config = None

    @classmethod
    def load(cls, config_path: str = "config/scraper_config.yaml") -> Dict[str, Any]:
        if cls._config:
            return cls._config

        if not os.path.exists(config_path):
            # Fallback defaults if file missing
            logging.warning(f"Config file {config_path} not found. Using defaults.")
            return cls._get_defaults()

        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            validate(instance=config, schema=CONFIG_SCHEMA)
            cls._config = config
            return config
        except ValidationError as e:
            raise ValueError(f"Invalid configuration in {config_path}: {e.message}")
        except Exception as e:
            raise RuntimeError(f"Failed to load config: {e}")

    @staticmethod
    def _get_defaults():
        return {
            "version": "1.0",
            "logging": {"level": "INFO", "json_format": True},
            "resources": {"max_workers_global": 100, "auto_tune": True},
            "rate_limiting": {"global_rpm": 120, "adaptive": False}
        }

    @classmethod
    def get(cls, *keys, default=None):
        """Safe nested get"""
        if not cls._config:
            cls.load()
        
        val = cls._config
        for key in keys:
            if isinstance(val, dict):
                val = val.get(key)
            else:
                return default
        
        return val if val is not None else default

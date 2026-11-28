"""YAML config loading."""

from typing import Any, Dict

import yaml


def _load_config(file_path: str) -> Dict[str, Any]:
    """Internal function to load config data from a YAML file with basic validation."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

    except yaml.YAMLError as e:
        print(f"Error: Malformed YAML syntax in '{file_path}': {e}. Using defaults.\n")
        return {}

    except Exception as e:
        print(f"Error: Could not read file '{file_path}': {e}. Using defaults.\n")
        return {}

    if not isinstance(config, dict):
        if config is None:
            return {}
        else:
            print(f"Error: Configuration file '{file_path}' must have a dictionary (map) as its root element, found '{type(config).__name__}'. Using defaults.\n")
            return {}

    return config

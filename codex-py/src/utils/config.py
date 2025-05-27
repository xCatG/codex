import json
import os
import yaml
from pathlib import Path
from typing import Dict, Optional, Union

from ..models import AppConfig, StoredConfig, ProviderInfo
from .default_providers import DEFAULT_PROVIDERS

# Configuration paths
CONFIG_DIR_NAME = ".codex-py"
CONFIG_DIR = Path.home() / CONFIG_DIR_NAME
CONFIG_JSON_NAME = "config.json"
CONFIG_YAML_NAME = "config.yaml" # Allow YAML for more human-friendly editing
INSTRUCTIONS_MD_NAME = "instructions.md"
DEFAULT_INSTRUCTIONS = "You are a helpful AI assistant. Please perform the requested file operations."

# Default values for AppConfig
DEFAULT_MODEL = "gpt-4" # Or choose another sensible default
DEFAULT_PROVIDER = "openai" # Should be a key in DEFAULT_PROVIDERS
DEFAULT_APPROVAL_MODE = "auto"

# OpenAI specific constants
AZURE_OPENAI_API_VERSION = "2023-07-01-preview" # Common version, can be made configurable
OPENAI_TIMEOUT_MS = 30000  # 30 seconds, can be made configurable

def _ensure_config_dir_exists():
    """Ensures the config directory exists, creates it if not."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

def _get_config_filepath() -> Optional[Path]:
    """Determines the path to the config file (JSON or YAML)."""
    _ensure_config_dir_exists()
    json_path = CONFIG_DIR / CONFIG_JSON_NAME
    yaml_path = CONFIG_DIR / CONFIG_YAML_NAME

    if json_path.exists():
        return json_path
    if yaml_path.exists():
        return yaml_path
    return None # No config file found

def _load_raw_from_file(filepath: Path) -> Dict:
    """Loads raw config data from JSON or YAML file."""
    try:
        with open(filepath, 'r') as f:
            if filepath.suffix == ".json":
                return json.load(f)
            elif filepath.suffix in [".yaml", ".yml"]:
                return yaml.safe_load(f)
    except Exception: # Broad exception for file reading/parsing errors
        # Log this error or handle more gracefully
        pass
    return {}

def _bootstrap_default_config_file():
    """Creates a default config file if none exists."""
    if not _get_config_filepath():
        default_config_path = CONFIG_DIR / CONFIG_JSON_NAME # Default to JSON for bootstrap
        default_stored_config = StoredConfig(
            model=DEFAULT_MODEL,
            provider=DEFAULT_PROVIDER,
            approvalMode=DEFAULT_APPROVAL_MODE,
            instructions=DEFAULT_INSTRUCTIONS,
            providers={name: info.model_dump(exclude_none=True) for name, info in DEFAULT_PROVIDERS.items()},
            default_provider=DEFAULT_PROVIDER
        )
        with open(default_config_path, 'w') as f:
            json.dump(default_stored_config.model_dump(exclude_none=True, by_alias=True), f, indent=2)
        print(f"Created default config file at {default_config_path}")


def load_config() -> AppConfig:
    """
    Loads configuration from file, environment variables, and defaults.
    Order of precedence:
    1. Environment variables (for API keys, specific base URLs)
    2. Values from config file (config.json or config.yaml)
    3. Default provider configurations (DEFAULT_PROVIDERS)
    4. Hardcoded default values
    """
    _ensure_config_dir_exists()
    _bootstrap_default_config_file() # Create default config if none exists

    config_filepath = _get_config_filepath()
    raw_file_config = {}
    if config_filepath:
        raw_file_config = _load_raw_from_file(config_filepath)

    # Start with an empty AppConfig or one based on raw_file_config
    # Pydantic will handle validation and default values defined in the model
    app_config_data = {**raw_file_config}

    # Initialize providers dictionary if not present
    if "providers" not in app_config_data or not app_config_data["providers"]:
        app_config_data["providers"] = {}

    # Merge with DEFAULT_PROVIDERS (file config can override defaults)
    for name, default_info in DEFAULT_PROVIDERS.items():
        if name not in app_config_data["providers"]:
            app_config_data["providers"][name] = default_info.model_dump(exclude_none=True)
        else:
            # Ensure all fields from default_info are present if not in file
            for key, value in default_info.model_dump(exclude_none=True).items():
                if key not in app_config_data["providers"][name]:
                    app_config_data["providers"][name][key] = value


    # Load API keys and base URLs from environment variables
    # Environment variables override file and default configurations for these specific fields
    for name, provider_data in app_config_data["providers"].items():
        provider_info_model = ProviderInfo(**provider_data) # To access env_key easily

        # API Key
        if provider_info_model.env_key:
            env_api_key = os.getenv(provider_info_model.env_key)
            if env_api_key:
                app_config_data["providers"][name]["api_key"] = env_api_key
            elif "api_key" not in app_config_data["providers"][name]: # if no env key and no key in file
                 app_config_data["providers"][name]["api_key"] = None


        # Base URL (e.g., OLLAMA_BASE_URL)
        # Specific env var like PROVIDERNAME_BASE_URL takes precedence
        specific_base_url_env = os.getenv(f"{name.upper()}_BASE_URL")
        if specific_base_url_env:
            app_config_data["providers"][name]["base_url"] = specific_base_url_env
        # For Ollama, also check generic OLLAMA_BASE_URL if specific not set
        elif name == "ollama" and os.getenv("OLLAMA_BASE_URL"):
             app_config_data["providers"][name]["base_url"] = os.getenv("OLLAMA_BASE_URL")
        elif "base_url" not in app_config_data["providers"][name]: # if no env var and no base_url in file
            # It might have been set by DEFAULT_PROVIDERS, or it might be None
            app_config_data["providers"][name]["base_url"] = DEFAULT_PROVIDERS.get(name, ProviderInfo(name=name)).base_url


    # Determine current provider and its API key for the top-level AppConfig
    current_provider_name = app_config_data.get("provider", DEFAULT_PROVIDER)
    if current_provider_name in app_config_data["providers"]:
        current_provider_data = app_config_data["providers"][current_provider_name]
        app_config_data["api_key"] = current_provider_data.get("api_key")
        # Base URL for the current provider can also be set at top level if needed,
        # but usually accessed via get_base_url

    # Apply defaults for top-level AppConfig fields if not set
    if "model" not in app_config_data or not app_config_data["model"]:
        app_config_data["model"] = DEFAULT_MODEL
    if "approvalMode" not in app_config_data or not app_config_data["approvalMode"]:
        app_config_data["approvalMode"] = DEFAULT_APPROVAL_MODE
    if "instructions" not in app_config_data or not app_config_data["instructions"]:
        # TODO: Load instructions from INSTRUCTIONS_MD_NAME
        app_config_data["instructions"] = DEFAULT_INSTRUCTIONS
    if "default_provider" not in app_config_data or not app_config_data["default_provider"]:
        app_config_data["default_provider"] = DEFAULT_PROVIDER


    return AppConfig(**app_config_data)


def save_config(config: AppConfig):
    """Saves the StoredConfig relevant parts of the AppConfig to the config file."""
    _ensure_config_dir_exists()
    
    # Default to JSON if no config file exists, otherwise use the existing format.
    config_filepath = _get_config_filepath()
    if not config_filepath:
        config_filepath = CONFIG_DIR / CONFIG_JSON_NAME
    
    # Prepare StoredConfig data from AppConfig
    # We only want to save fields that are part of StoredConfig
    stored_config_data = StoredConfig(
        model=config.model,
        provider=config.provider,
        approvalMode=config.approvalMode,
        instructions=config.instructions, # Potentially save instructions back if they are not from file
        providers={name: info.model_dump(exclude_none=True, exclude={"api_key"} if not info.api_key else {}) # Don't save api_key if None
                   for name, info in config.providers.items()},
        default_provider=config.default_provider
    ).model_dump(exclude_none=True, by_alias=True)

    try:
        with open(config_filepath, 'w') as f:
            if config_filepath.suffix == ".json":
                json.dump(stored_config_data, f, indent=2)
            elif config_filepath.suffix in [".yaml", ".yml"]:
                yaml.dump(stored_config_data, f, indent=2, sort_keys=False)
        # print(f"Configuration saved to {config_filepath}")
    except Exception as e:
        print(f"Error saving configuration to {config_filepath}: {e}")


def get_api_key(provider_name: str, config: AppConfig) -> Optional[str]:
    """Gets the API key for a specific provider from the AppConfig."""
    provider_info = config.providers.get(provider_name)
    if provider_info:
        return provider_info.api_key
    return None

def get_base_url(provider_name: str, config: AppConfig) -> Optional[str]:
    """Gets the base URL for a specific provider from the AppConfig."""
    provider_info = config.providers.get(provider_name)
    if provider_info:
        return provider_info.base_url
    return None

def set_api_key(api_key: str, provider_name: str, config: AppConfig) -> AppConfig:
    """
    Sets the API key for a specific provider in the AppConfig.
    This updates the runtime AppConfig. To persist, call save_config.
    """
    if provider_name in config.providers:
        config.providers[provider_name].api_key = api_key
        # If this is the currently active provider, update the top-level api_key too
        if config.provider == provider_name:
            config.api_key = api_key
    else:
        # If provider doesn't exist, create it (might happen if config is minimal)
        new_provider_info = ProviderInfo(name=provider_name, api_key=api_key)
        config.providers[provider_name] = new_provider_info
    return config # Return modified config


# Example Usage (can be run with `python -m codex-py.src.utils.config` from root of `codex-py` project for testing)
if __name__ == "__main__":
    print(f"Config directory: {CONFIG_DIR}")

    # Test loading (will create default if not exists)
    app_config = load_config()
    print("\nLoaded AppConfig:")
    print(app_config.model_dump_json(indent=2, exclude_none=True))

    # Test getting API key and base URL for the default provider
    default_prov_name = app_config.default_provider or DEFAULT_PROVIDER
    print(f"\nDefault provider from config: {default_prov_name}")
    
    api_key = get_api_key(default_prov_name, app_config)
    base_url = get_base_url(default_prov_name, app_config)
    print(f"API Key for {default_prov_name}: {api_key}")
    print(f"Base URL for {default_prov_name}: {base_url}")

    # Test setting an API key (runtime only)
    if default_prov_name == "openai": # Example for openai
        print(f"\nSetting API key for {default_prov_name} (runtime)...")
        app_config = set_api_key("sk-test12345", default_prov_name, app_config)
        print(f"New API Key for {default_prov_name} (runtime): {get_api_key(default_prov_name, app_config)}")
        print(f"AppConfig current api_key: {app_config.api_key}")


    # Test saving - modify something
    app_config.model = "gpt-4-turbo-preview"
    app_config.approvalMode = "manual"
    # Simulate adding a new provider or modifying existing one for saving
    if "new_dummy_provider" not in app_config.providers:
        app_config.providers["new_dummy_provider"] = ProviderInfo(name="New Dummy Provider", base_url="http://localhost:8080", env_key="DUMMY_KEY", api_key="dummykey123")
    else:
        app_config.providers["new_dummy_provider"].base_url = "http://localhost:8081"

    print("\nSaving modified AppConfig...")
    save_config(app_config)

    print("\nRe-loading config to verify save...")
    reloaded_config = load_config()
    print(reloaded_config.model_dump_json(indent=2, exclude_none=True))

    # Cleanup: remove the test config dir if you want
    # import shutil
    # if CONFIG_DIR.exists() and CONFIG_DIR_NAME == ".codex-py-test": # Safety check
    #     shutil.rmtree(CONFIG_DIR)
    #     print(f"\nCleaned up test config directory: {CONFIG_DIR}")
    # else:
    #     print(f"\nSkipping cleanup, {CONFIG_DIR} not a test directory or doesn't exist.")

    print(f"\nTo test further, set environment variables like OPENAI_API_KEY and run again.")
    print(f"Or modify {CONFIG_DIR / CONFIG_JSON_NAME} or {CONFIG_DIR / CONFIG_YAML_NAME}")

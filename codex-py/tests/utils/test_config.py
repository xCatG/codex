import pytest
import os
import json
import yaml
from pathlib import Path
from unittest.mock import mock_open, MagicMock

# Assuming PYTHONPATH is set up so that 'src' is accessible
from src.utils.config import (
    load_config,
    save_config,
    get_api_key,
    get_base_url,
    set_api_key,
    AppConfig,
    StoredConfig,
    ProviderInfo,
    CONFIG_DIR,
    CONFIG_JSON_NAME,
    CONFIG_YAML_NAME,
    DEFAULT_MODEL,
    DEFAULT_PROVIDER,
    DEFAULT_APPROVAL_MODE,
    DEFAULT_INSTRUCTIONS,
    DEFAULT_PROVIDERS
)

# Helper to reset relevant environment variables before each test
@pytest.fixture(autouse=True)
def reset_env_vars(monkeypatch):
    env_vars_to_clear = [
        "OPENAI_API_KEY", "AZURE_OPENAI_API_KEY", "OLLAMA_BASE_URL", 
        "ANTHROPIC_API_KEY", "GOOGLE_API_KEY", "MISTRAL_API_KEY",
        "CODEX_MODEL", "CODEX_PROVIDER", "CODEX_APPROVAL_MODE",
        # For specific provider base URLs
        "OPENAI_BASE_URL", "AZURE_BASE_URL" 
    ]
    for var in env_vars_to_clear:
        monkeypatch.delenv(var, raising=False)

@pytest.fixture
def mock_config_dir(mocker):
    mocker.patch.object(Path, 'exists', return_value=True) # Assume config dir exists
    mocker.patch.object(Path, 'is_file', return_value=True)
    mocker.patch.object(Path, 'mkdir') # Mock mkdir

def test_load_config_defaults(mocker, mock_config_dir):
    """Test loading config with no existing files and no env vars, expecting defaults."""
    mocker.patch('src.utils.config._get_config_filepath', return_value=None) # No config file
    mocker.patch('os.getenv', return_value=None) # No relevant env vars

    # Mock open for the bootstrap process
    mock_file_open = mock_open()
    mocker.patch('builtins.open', mock_file_open)

    config = load_config()

    assert isinstance(config, AppConfig)
    assert config.model == DEFAULT_MODEL
    assert config.provider == DEFAULT_PROVIDER
    assert config.approvalMode == DEFAULT_APPROVAL_MODE
    assert config.instructions == DEFAULT_INSTRUCTIONS
    assert config.api_key is None # Default provider (OpenAI) key not set by default

    # Check that default providers are loaded
    assert "openai" in config.providers
    assert config.providers["openai"].name == "OpenAI"
    assert config.providers["openai"].base_url == DEFAULT_PROVIDERS["openai"].base_url
    
    # Check that bootstrap tried to write a default config
    mock_file_open.assert_called_once_with(CONFIG_DIR / CONFIG_JSON_NAME, 'w')


def test_load_config_env_var_override(mocker, mock_config_dir):
    """Test that environment variables override defaults."""
    mocker.patch('src.utils.config._get_config_filepath', return_value=None) # No config file

    # Mock os.getenv
    env_map = {
        "OPENAI_API_KEY": "sk-env-openai",
        "AZURE_OPENAI_API_KEY": "env-azure-key",
        "CODEX_MODEL": "env-model",
        "CODEX_PROVIDER": "azure", # Change provider
        "CODEX_APPROVAL_MODE": "manual",
        "AZURE_BASE_URL": "https://env-azure.openai.com"
    }
    mocker.patch('os.getenv', lambda k, v=None: env_map.get(k, v))
    
    mocker.patch('builtins.open', mock_open()) # For bootstrap

    config = load_config()

    assert config.model == "env-model"
    assert config.provider == "azure"
    assert config.approvalMode == "manual"
    assert config.api_key == "env-azure-key" # API key for 'azure' provider
    assert config.providers["openai"].api_key == "sk-env-openai"
    assert config.providers["azure"].api_key == "env-azure-key"
    assert config.providers["azure"].base_url == "https://env-azure.openai.com"


def test_load_config_from_json_file(mocker, mock_config_dir):
    """Test loading configuration from a JSON file."""
    json_content = {
        "model": "test-model-json",
        "provider": "openai",
        "approvalMode": "none",
        "instructions": "JSON instructions",
        "providers": {
            "openai": {"api_key": "sk-json-openai", "base_url": "json-openai-url"},
            "custom_provider": {"name": "Custom", "api_key": "customkey"}
        },
        "default_provider": "openai"
    }
    mock_file_open = mock_open(read_data=json.dumps(json_content))
    mocker.patch('builtins.open', mock_file_open)
    
    json_path = CONFIG_DIR / CONFIG_JSON_NAME
    mocker.patch('src.utils.config._get_config_filepath', return_value=json_path)
    mocker.patch.object(Path, 'suffix', '.json') # Ensure suffix is json for this path

    config = load_config()

    assert config.model == "test-model-json"
    assert config.provider == "openai"
    assert config.approvalMode == "none"
    assert config.instructions == "JSON instructions"
    assert config.api_key == "sk-json-openai" # Current provider is openai
    assert config.providers["openai"].api_key == "sk-json-openai"
    assert config.providers["openai"].base_url == "json-openai-url"
    assert "custom_provider" in config.providers
    assert config.providers["custom_provider"].api_key == "customkey"


def test_load_config_from_yaml_file(mocker, mock_config_dir):
    """Test loading configuration from a YAML file."""
    yaml_content = {
        "model": "test-model-yaml",
        "provider": "ollama", # Different provider
        "providers": {
            "ollama": {"base_url": "http://yaml-ollama:11434"}
        }
    }
    mock_file_open = mock_open(read_data=yaml.dump(yaml_content))
    mocker.patch('builtins.open', mock_file_open)
    
    yaml_path = CONFIG_DIR / CONFIG_YAML_NAME
    mocker.patch('src.utils.config._get_config_filepath', return_value=yaml_path)
    mocker.patch.object(Path, 'suffix', '.yaml')

    config = load_config()

    assert config.model == "test-model-yaml"
    assert config.provider == "ollama"
    assert config.providers["ollama"].base_url == "http://yaml-ollama:11434"
    # API key for ollama might be None by default, which is fine
    assert config.api_key is None 

def test_get_api_key_and_base_url(monkeypatch):
    """Test get_api_key and get_base_url utility functions."""
    # Mock environment for a specific provider key
    monkeypatch.setenv("MISTRAL_API_KEY", "sk-mistral-test")

    # Load config - this will pick up the MISTRAL_API_KEY from env
    config = load_config() 
    
    assert get_api_key("mistral", config) == "sk-mistral-test"
    assert get_base_url("mistral", config) == DEFAULT_PROVIDERS["mistral"].base_url

    assert get_api_key("openai", config) is None # No OPENAI_API_KEY set in this test
    assert get_base_url("openai", config) == DEFAULT_PROVIDERS["openai"].base_url
    
    # Test a provider not in defaults (if config allows dynamic addition, or if it was loaded)
    # For this test, let's assume it's not there.
    assert get_api_key("non_existent_provider", config) is None
    assert get_base_url("non_existent_provider", config) is None


def test_set_api_key(monkeypatch):
    """Test the set_api_key function."""
    config = load_config() # Start with a default config

    # Set API key for the current default provider (openai)
    config = set_api_key("sk-new-openai", "openai", config)
    assert config.providers["openai"].api_key == "sk-new-openai"
    assert config.api_key == "sk-new-openai" # Should also update top-level key

    # Set API key for a different provider
    config = set_api_key("sk-new-anthropic", "anthropic", config)
    assert config.providers["anthropic"].api_key == "sk-new-anthropic"
    # Current provider is still openai, so top-level key should not change yet
    assert config.api_key == "sk-new-openai" 

    # Change current provider to anthropic
    config.provider = "anthropic"
    # Manually update top-level api_key (as set_api_key does if provider matches)
    config.api_key = config.providers["anthropic"].api_key 
    assert config.api_key == "sk-new-anthropic"

    # Set API key for a provider not initially in config.providers (e.g. a new one)
    config = set_api_key("sk-custom-key", "custom_provider", config)
    assert "custom_provider" in config.providers
    assert config.providers["custom_provider"].name == "custom_provider" # Name is set to key
    assert config.providers["custom_provider"].api_key == "sk-custom-key"


def test_save_config_json(mocker, mock_config_dir):
    """Test saving configuration to a JSON file."""
    mock_file_open = mock_open()
    mocker.patch('builtins.open', mock_file_open)
    
    json_path = CONFIG_DIR / CONFIG_JSON_NAME
    mocker.patch('src.utils.config._get_config_filepath', return_value=json_path) # Pretend JSON exists
    mocker.patch.object(Path, 'suffix', '.json')

    config = load_config() # Get a default config
    config.model = "saved-model"
    config.providers["openai"].api_key = "sk-savedkey" # API keys should be saved if present
    config.providers["new_prov"] = ProviderInfo(name="NewProv", api_key="newkey123")


    save_config(config)

    mock_file_open.assert_called_once_with(json_path, 'w')
    # Check what was written to the file
    written_content = mock_file_open().write.call_args[0][0]
    saved_data = json.loads(written_content)
    
    assert saved_data["model"] == "saved-model"
    assert saved_data["providers"]["openai"]["api_key"] == "sk-savedkey"
    assert "new_prov" in saved_data["providers"]
    assert saved_data["providers"]["new_prov"]["api_key"] == "newkey123"
    # Ensure fields that should be excluded if None are not present (e.g. env_key if not set)
    assert "env_key" not in saved_data["providers"]["new_prov"] 


def test_save_config_yaml(mocker, mock_config_dir):
    """Test saving configuration to a YAML file."""
    mock_file_open = mock_open()
    mocker.patch('builtins.open', mock_file_open)
    
    yaml_path = CONFIG_DIR / CONFIG_YAML_NAME
    mocker.patch('src.utils.config._get_config_filepath', return_value=yaml_path) # Pretend YAML exists
    mocker.patch.object(Path, 'suffix', '.yaml')

    config = load_config()
    config.model = "yaml-saved-model"
    config.providers["ollama"] = ProviderInfo(name="Ollama", base_url="http://ollama-yaml")
    
    save_config(config)

    mock_file_open.assert_called_once_with(yaml_path, 'w')
    written_content = mock_file_open().write.call_args[0][0]
    saved_data = yaml.safe_load(written_content)
    
    assert saved_data["model"] == "yaml-saved-model"
    assert saved_data["providers"]["ollama"]["base_url"] == "http://ollama-yaml"


def test_first_run_bootstrap_creates_files(mocker):
    """Test that default config and instructions files are created on first run."""
    # Mock Path.exists to return False for all relevant files initially
    mocker.patch.object(Path, 'exists', return_value=False)
    
    # Mock os.makedirs and builtins.open
    mock_makedirs = mocker.patch('os.makedirs') # Path.mkdir calls this
    mocker.patch.object(Path, 'mkdir', side_effect=lambda parents=True, exist_ok=True: mock_makedirs(CONFIG_DIR) if parents else None)

    mock_file_open = mock_open()
    mocker.patch('builtins.open', mock_file_open)

    # Mock _get_config_filepath to initially return None, then path after bootstrap
    # This is a bit tricky; simpler to just check calls to open()
    mocker.patch('src.utils.config._get_config_filepath', return_value=None)

    load_config()

    # Assert that config directory was attempted to be created
    # CONFIG_DIR.mkdir(parents=True, exist_ok=True) is called in _ensure_config_dir_exists
    # which is called by _get_config_filepath and _bootstrap_default_config_file
    # Path.mkdir is called by _ensure_config_dir_exists
    assert Path.mkdir.call_count > 0 # called by _ensure_config_dir_exists

    # Assert that the default config file was opened for writing
    # The bootstrap function defaults to JSON
    default_config_path = CONFIG_DIR / CONFIG_JSON_NAME
    
    # Check if open was called for the config file
    # The calls list contains all calls to the mock_open object
    # We need to check if a call matches (default_config_path, 'w')
    found_config_write = False
    for call_args in mock_file_open.call_args_list:
        if call_args[0][0] == default_config_path and call_args[0][1] == 'w':
            found_config_write = True
            # Verify content of default config (simplified check)
            written_content_config = mock_file_open(default_config_path, 'w').write.call_args[0][0]
            default_data = json.loads(written_content_config)
            assert default_data["model"] == DEFAULT_MODEL
            assert default_data["provider"] == DEFAULT_PROVIDER
            break
    assert found_config_write, f"Default config file {default_config_path} was not written during bootstrap."

    # Note: The instructions file is not created by load_config itself,
    # but by the CLI when --config is used. So, not testing its creation here.


if __name__ == "__main__":
    pytest.main([__file__])

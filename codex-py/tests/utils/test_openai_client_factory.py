import pytest
from unittest.mock import patch # Using patch directly from unittest.mock

from openai import OpenAI, AzureOpenAI

# Assuming PYTHONPATH is set up so that 'src' is accessible
from src.utils.openai_client_factory import create_openai_client
from src.models import AppConfig, ProviderInfo
from src.utils.config import AZURE_OPENAI_API_VERSION, OPENAI_TIMEOUT_MS

@pytest.fixture
def base_app_config():
    """A base AppConfig fixture that can be customized by tests."""
    return AppConfig(
        model="test-model",
        provider="openai", # Default provider for this base fixture
        api_key="sk-dummykey", # Default API key for the current provider
        providers={
            "openai": ProviderInfo(
                name="OpenAI",
                api_key="sk-openaikey",
                base_url="https://api.openai.com/v1", # Default OpenAI URL
                env_key="OPENAI_API_KEY"
            ),
            "azure": ProviderInfo(
                name="Azure OpenAI",
                api_key="azurekey-dummy",
                base_url="https://dummy-azure-endpoint.openai.azure.com",
                env_key="AZURE_OPENAI_API_KEY"
            ),
            "ollama": ProviderInfo(
                name="Ollama",
                base_url="http://localhost:11434", # Default Ollama URL
                api_key=None # Ollama might not use API keys
            ),
            "custom_oai_compat": ProviderInfo(
                name="Custom OpenAI Compatible",
                api_key="customkey123",
                base_url="http://custom.api.example.com:8080/v1"
            )
        }
    )

@patch('openai.OpenAI') # Mocks openai.OpenAI globally for this test
def test_create_openai_client_for_openai_provider(MockOpenAI, base_app_config):
    """Test creation of OpenAI client for the 'openai' provider."""
    app_config = base_app_config
    app_config.provider = "openai"
    # Ensure the top-level api_key reflects the current provider's key
    app_config.api_key = app_config.providers["openai"].api_key 
    
    client = create_openai_client(app_config)

    MockOpenAI.assert_called_once_with(
        api_key=app_config.providers["openai"].api_key,
        base_url=app_config.providers["openai"].base_url, # Should be called with explicit base_url for OpenAI
        timeout=OPENAI_TIMEOUT_MS / 1000.0
        # default_headers can be checked if we add them
    )
    assert isinstance(client, MockOpenAI) # Client is the mocked instance

@patch('openai.AzureOpenAI') # Mocks openai.AzureOpenAI
def test_create_openai_client_for_azure_provider(MockAzureOpenAI, base_app_config):
    """Test creation of AzureOpenAI client for the 'azure' provider."""
    app_config = base_app_config
    app_config.provider = "azure"
    app_config.api_key = app_config.providers["azure"].api_key

    client = create_openai_client(app_config)

    MockAzureOpenAI.assert_called_once_with(
        api_key=app_config.providers["azure"].api_key,
        azure_endpoint=app_config.providers["azure"].base_url,
        api_version=AZURE_OPENAI_API_VERSION,
        timeout=OPENAI_TIMEOUT_MS / 1000.0
    )
    assert isinstance(client, MockAzureOpenAI)

@patch('openai.OpenAI')
def test_create_openai_client_for_ollama_provider(MockOpenAI, base_app_config):
    """Test creation of OpenAI client for 'ollama' (OpenAI compatible)."""
    app_config = base_app_config
    app_config.provider = "ollama"
    app_config.api_key = app_config.providers["ollama"].api_key # Should be None

    client = create_openai_client(app_config)

    MockOpenAI.assert_called_once_with(
        api_key=None, # Ollama typically doesn't use API keys
        base_url=app_config.providers["ollama"].base_url,
        timeout=OPENAI_TIMEOUT_MS / 1000.0
    )
    assert isinstance(client, MockOpenAI)

@patch('openai.OpenAI')
def test_create_openai_client_for_custom_openai_compatible_provider(MockOpenAI, base_app_config):
    """Test with a custom provider from AppConfig that is OpenAI compatible."""
    app_config = base_app_config
    app_config.provider = "custom_oai_compat"
    app_config.api_key = app_config.providers["custom_oai_compat"].api_key

    client = create_openai_client(app_config)

    MockOpenAI.assert_called_once_with(
        api_key=app_config.providers["custom_oai_compat"].api_key,
        base_url=app_config.providers["custom_oai_compat"].base_url,
        timeout=OPENAI_TIMEOUT_MS / 1000.0
    )
    assert isinstance(client, MockOpenAI)


def test_create_openai_client_missing_provider_config(base_app_config):
    """Test client creation when provider config is missing."""
    app_config = base_app_config
    app_config.provider = "non_existent_provider"
    app_config.api_key = None # No key for non-existent provider

    with pytest.raises(ValueError) as excinfo:
        create_openai_client(app_config)
    assert "Configuration for provider 'non_existent_provider' not found" in str(excinfo.value)

def test_create_openai_client_missing_api_key_for_openai(base_app_config):
    """Test client creation for OpenAI provider when API key is missing."""
    app_config = base_app_config
    app_config.provider = "openai"
    app_config.providers["openai"].api_key = None # Simulate missing API key
    app_config.api_key = None


    with pytest.raises(ValueError) as excinfo:
        create_openai_client(app_config)
    assert "API key for provider 'openai' is missing" in str(excinfo.value)


def test_create_openai_client_missing_base_url_for_azure(base_app_config):
    """Test client creation for Azure provider when base_url (endpoint) is missing."""
    app_config = base_app_config
    app_config.provider = "azure"
    app_config.providers["azure"].base_url = None # Simulate missing base_url
    app_config.api_key = app_config.providers["azure"].api_key # API key is present


    with pytest.raises(ValueError) as excinfo:
        create_openai_client(app_config)
    assert "Base URL (Azure OpenAI endpoint) is required for Azure provider" in str(excinfo.value)

if __name__ == "__main__":
    pytest.main([__file__])

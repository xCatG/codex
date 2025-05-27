from openai import OpenAI, AzureOpenAI, DefaultHttpxClient
from typing import Union, Optional

try:
    from ..models import AppConfig, ProviderInfo
    from .config import get_api_key, get_base_url, AZURE_OPENAI_API_VERSION, OPENAI_TIMEOUT_MS
except ImportError: # Fallback for simpler execution contexts
    from models import AppConfig, ProviderInfo
    from utils.config import get_api_key, get_base_url, AZURE_OPENAI_API_VERSION, OPENAI_TIMEOUT_MS


def create_openai_client(app_config: AppConfig) -> Union[OpenAI, AzureOpenAI]:
    """
    Creates and configures an OpenAI or AzureOpenAI client based on the AppConfig.
    """
    provider_name = app_config.provider
    if not provider_name:
        raise ValueError("Provider name is not configured in AppConfig.")

    provider_info: Optional[ProviderInfo] = app_config.providers.get(provider_name)
    if not provider_info:
        raise ValueError(f"Configuration for provider '{provider_name}' not found.")

    api_key = provider_info.api_key # Already resolved in load_config
    base_url = provider_info.base_url # Already resolved in load_config

    if not api_key and provider_name not in ["ollama"]: # Ollama might not require an API key
        raise ValueError(f"API key for provider '{provider_name}' is missing.")

    # Common client arguments
    client_args = {
        "api_key": api_key,
        "timeout": OPENAI_TIMEOUT_MS / 1000.0, # OpenAI SDK expects seconds
        # Default headers can be added here if needed, e.g., for Organization, Project
        # "default_headers": { "OpenAI-Organization": "org-...", "OpenAI-Project": "project-..." }
        # Http client with proxies can be configured here if needed
        # "http_client": DefaultHttpxClient(proxies=app_config.proxies) if app_config.proxies else None
    }

    if provider_name == "azure":
        if not base_url:
            raise ValueError("Base URL (Azure OpenAI endpoint) is required for Azure provider.")
        
        # Azure specific environment variable for deployment name if needed
        # azure_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT") 
        # model in AppConfig is often used as deployment name for Azure
        
        return AzureOpenAI(
            azure_endpoint=base_url,
            api_version=AZURE_OPENAI_API_VERSION, # Make sure this is available in config or constants
            **client_args
        )
    else: # Handles "openai", "ollama", and other compatible providers
        if base_url: # For providers like Ollama or custom OpenAI-compatible endpoints
            client_args["base_url"] = base_url
        
        # For "openai" provider, base_url is typically not set in args unless overriding default
        # If provider_name is "openai" and base_url is None, it will use the default OpenAI URL.
        return OpenAI(**client_args)

if __name__ == '__main__':
    # Example Usage (requires AppConfig and related structures to be defined/mocked)
    print("Testing OpenAI Client Factory...")

    # Mock AppConfig for testing
    mock_openai_provider = ProviderInfo(name="OpenAI", env_key="OPENAI_API_KEY", api_key="sk-testkeyopenai123")
    mock_azure_provider = ProviderInfo(name="Azure OpenAI", base_url="https://test-azure.openai.azure.com", env_key="AZURE_OPENAI_API_KEY", api_key="testkeyazure123")
    mock_ollama_provider = ProviderInfo(name="Ollama", base_url="http://localhost:11434")


    test_config_openai = AppConfig(
        model="gpt-4",
        provider="openai",
        api_key=mock_openai_provider.api_key, # Top-level api_key
        providers={"openai": mock_openai_provider}
    )
    test_config_azure = AppConfig(
        model="gpt-35-turbo", # Often corresponds to Azure deployment name
        provider="azure",
        api_key=mock_azure_provider.api_key, # Top-level api_key
        providers={"azure": mock_azure_provider}
    )
    test_config_ollama = AppConfig(
        model="llama2",
        provider="ollama",
        providers={"ollama": mock_ollama_provider}
    )
    
    print("\n--- Testing OpenAI client ---")
    try:
        client_openai = create_openai_client(test_config_openai)
        print(f"OpenAI client created: {type(client_openai)}")
        print(f"API Key: {client_openai.api_key[:7]}...")
        print(f"Base URL: {client_openai.base_url}")
    except Exception as e:
        print(f"Error creating OpenAI client: {e}")

    print("\n--- Testing Azure OpenAI client ---")
    try:
        client_azure = create_openai_client(test_config_azure)
        print(f"Azure OpenAI client created: {type(client_azure)}")
        print(f"API Key: {client_azure.api_key[:7]}...")
        print(f"Base URL (Azure Endpoint): {client_azure.base_url}")
        # print(f"API Version: {client_azure.api_version}") # Not directly available like this
    except Exception as e:
        print(f"Error creating Azure client: {e}")

    print("\n--- Testing Ollama client (via OpenAI client) ---")
    try:
        client_ollama = create_openai_client(test_config_ollama)
        print(f"Ollama client created: {type(client_ollama)}")
        print(f"API Key: {client_ollama.api_key}") # Expected to be None or placeholder
        print(f"Base URL: {client_ollama.base_url}")
    except Exception as e:
        print(f"Error creating Ollama client: {e}")

    print("\n--- Testing Missing API Key (for OpenAI) ---")
    test_config_openai_no_key = AppConfig(
        model="gpt-4",
        provider="openai",
        providers={"openai": ProviderInfo(name="OpenAI", env_key="OPENAI_API_KEY", api_key=None)}
    )
    try:
        create_openai_client(test_config_openai_no_key)
    except ValueError as e:
        print(f"Correctly caught error for missing API key: {e}")
    
    print("\n--- Testing Missing Base URL (for Azure) ---")
    test_config_azure_no_base = AppConfig(
        model="gpt-35-turbo",
        provider="azure",
        api_key="somekey",
        providers={"azure": ProviderInfo(name="Azure OpenAI", env_key="AZURE_OPENAI_API_KEY", api_key="somekey", base_url=None)}
    )
    try:
        create_openai_client(test_config_azure_no_base)
    except ValueError as e:
        print(f"Correctly caught error for missing Azure base URL: {e}")

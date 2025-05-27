from ..models import ProviderInfo

DEFAULT_PROVIDERS = {
    "openai": ProviderInfo(
        name="OpenAI",
        base_url="https://api.openai.com/v1",
        env_key="OPENAI_API_KEY",
    ),
    "azure": ProviderInfo(
        name="Azure OpenAI",
        base_url=None,  # User needs to set this
        env_key="AZURE_OPENAI_API_KEY",
    ),
    "ollama": ProviderInfo(
        name="Ollama",
        base_url="http://localhost:11434", # Default, can be overridden by env OLLAMA_BASE_URL
        env_key=None, # No API key needed for local Ollama usually
    ),
    "anthropic": ProviderInfo(
        name="Anthropic",
        base_url="https://api.anthropic.com/v1",
        env_key="ANTHROPIC_API_KEY",
    ),
    "google": ProviderInfo(
        name="Google",
        base_url=None, # Gemini API has a different structure, may need specific handling
        env_key="GOOGLE_API_KEY",
    ),
    "mistral": ProviderInfo(
        name="Mistral AI",
        base_url="https://api.mistral.ai/v1",
        env_key="MISTRAL_API_KEY",
    ),
    # Add other providers as needed
}

# To handle OLLAMA_BASE_URL if set
import os
ollama_base_url_env = os.getenv("OLLAMA_BASE_URL")
if ollama_base_url_env and "ollama" in DEFAULT_PROVIDERS:
    DEFAULT_PROVIDERS["ollama"].base_url = ollama_base_url_env

if __name__ == "__main__":
    for name, provider in DEFAULT_PROVIDERS.items():
        print(f"Provider: {name}")
        print(f"  Name: {provider.name}")
        print(f"  Base URL: {provider.base_url}")
        print(f"  Env Key: {provider.env_key}")
        print("-" * 20)

import asyncio
from typing import Callable, Optional, Any

try:
import openai
from openai import (
    APIError,
    APIConnectionError,
    RateLimitError,
    APIStatusError,
    AuthenticationError,
    NotFoundError,
    ConflictError,
    PermissionDeniedError,
    UnprocessableEntityError
)
from typing import Callable, Optional, Any, AsyncGenerator

try:
    from ..models import AppConfig
    from ..utils.openai_client_factory import create_openai_client
except ImportError: # Fallback for simpler execution contexts
    from models import AppConfig
    from utils.openai_client_factory import create_openai_client

class AgentLoopPy:
    def __init__(self, app_config: AppConfig, 
                 on_item_callback: Optional[Callable[[str], None]] = None,
                 on_loading: Optional[Callable[[bool], None]] = None):
        self.app_config = app_config
        self.oai_client = create_openai_client(app_config)
        self.current_stream = None
        self.canceled = False
        self.on_item_callback = on_item_callback
        self.on_loading = on_loading
        self.transcript: list[dict] = []
        # The 'disable_response_storage' flag is not directly used in the Python SDK's
        # chat completion call in the same way it might be in a custom TS implementation
        # that manages response IDs. Here, we always send history.
        # It could be used later if we implement more complex history management.
        self.disable_response_storage = getattr(app_config, 'disable_response_storage', False)

    async def run(self, prompt: str) -> AsyncGenerator[str, None]:
        """
        Runs a streaming chat completion request, manages history, and yields content parts.
        """
        if self.canceled:
            print("AgentLoopPy: Run called after cancellation.")
            return

        if self.on_loading:
            self.on_loading(True)

        # Append user prompt to transcript
        self.transcript.append({"role": "user", "content": prompt})

        system_message_content = self.app_config.instructions or "You are a helpful assistant."
        messages_payload = [
            {"role": "system", "content": system_message_content}
        ] + self.transcript

        full_assistant_response = []
        try:
            self.current_stream = await self.oai_client.chat.completions.create(
                model=self.app_config.model,
                messages=messages_payload, # Send full history including current prompt
                stream=True
            )
            
            async for chunk in self.current_stream:
                if self.canceled:
                    print("AgentLoopPy: Operation cancelled during streaming.")
                    break
                
                if chunk.choices and len(chunk.choices) > 0:
                    content_part = chunk.choices[0].delta.content
                    if content_part:
                        full_assistant_response.append(content_part)
                        if self.on_item_callback:
                            self.on_item_callback(content_part)
                        yield content_part
            
        except openai.APIError as e:
            error_message = f"OpenAI API Error: {e}"
            print(f"AgentLoopPy: {error_message}")
            full_assistant_response.append(error_message) # Add error to response history
            if self.on_item_callback:
                self.on_item_callback(error_message)
            yield error_message
        except Exception as e:
            error_message = f"An unexpected error occurred: {e}"
            print(f"AgentLoopPy: {error_message}")
            full_assistant_response.append(error_message) # Add error to response history
            if self.on_item_callback:
                self.on_item_callback(error_message)
            yield error_message
        finally:
            if self.on_loading:
                self.on_loading(False)
            self.current_stream = None

            # Append full assistant response to transcript (if any content was generated)
            # Even if an error message was yielded, we store what was actually "said" by assistant
            final_response_str = "".join(full_assistant_response)
            if final_response_str: # Avoid adding empty assistant messages if stream was empty or only error
                self.transcript.append({"role": "assistant", "content": final_response_str})


    def clear_history(self):
        """Clears the conversation transcript."""
        self.transcript = []
        print("AgentLoopPy: Conversation history cleared.")

    def cancel(self):
        """
        Requests cancellation of any ongoing operations.
        """
        self.canceled = True
        print("AgentLoopPy: Cancellation requested.")
        # For OpenAI's current stream object, breaking the loop is the main way.
        if self.current_stream:
            print("AgentLoopPy: Stream will be stopped on next iteration or chunk.")


if __name__ == '__main__':
    import asyncio
    import os
    try:
        from models import AppConfig, ProviderInfo 
        from utils.config import DEFAULT_PROVIDER, DEFAULT_MODEL, load_config
    except ImportError:
        print("Could not import. Ensure models.py and utils.config are accessible.")
        exit(1)

    async def main_test():
        print("Testing AgentLoopPy with history and streaming...")

        # Use load_config to get a more complete AppConfig, including providers
        # Ensure your environment has OPENAI_API_KEY set or config file has it.
        try:
            # This will try to load from ~/.codex-py/config.json or bootstrap one
            app_config = load_config() 
            # Override for testing if needed, or ensure your config is set up
            app_config.provider = os.getenv("CODEX_PROVIDER", "openai")
            app_config.model = os.getenv("CODEX_MODEL", "gpt-3.5-turbo")
            if app_config.provider == "openai" and not os.getenv("OPENAI_API_KEY"):
                 if not app_config.providers.get("openai", ProviderInfo(name="")).api_key:
                    print("OpenAI provider selected but no API key found in env or config. Test may fail.")
        except Exception as e:
            print(f"Error loading config for test: {e}")
            print("Using a minimal mock config for testing structure, API call will likely fail.")
            mock_openai_provider = ProviderInfo(name="OpenAI", api_key="sk-dummykeyifnotset")
            app_config = AppConfig(
                model="gpt-3.5-turbo", provider="openai", api_key=mock_openai_provider.api_key,
                providers={"openai": mock_openai_provider},
                instructions="You are a test assistant for streaming with history."
            )


        def my_stream_callback(token: str):
            # print(f"CB: '{token}'", end='', flush=True) # Verbose
            pass

        print(f"\nUsing Provider: {app_config.provider}, Model: {app_config.model}")
        agent_loop = AgentLoopPy(
            app_config=app_config,
            on_item_callback=my_stream_callback,
            on_loading=lambda loading: print(f"Loading: {loading}")
        )
        
        prompts = [
            "What is the capital of France?",
            "And what is its population?" # Follow-up question
        ]
        
        for i, p_text in enumerate(prompts):
            print(f"\nUser Prompt {i+1}: {p_text}")
            print("Assistant: ", end='', flush=True)
            full_response = ""
            try:
                async for content_part in agent_loop.run(p_text):
                    if content_part:
                        print(content_part, end='', flush=True)
                        full_response += content_part
                print("\n--- End of Stream ---")
                if not full_response.strip(): print("(No content streamed)")
            except Exception as e:
                print(f"\nAn error occurred: {e}")
            
            # Display current transcript after each interaction
            print(f"Transcript after prompt {i+1}:")
            for entry in agent_loop.transcript:
                print(f"  {entry['role']}: {entry['content'][:70]}...") # Print snippet
        
        print("\nClearing history...")
        agent_loop.clear_history()
        assert not agent_loop.transcript
        print("History cleared.")

        print("\nRunning one more prompt after clearing history (should have no context):")
        print("User Prompt: What was my first question?")
        print("Assistant: ", end='', flush=True)
        async for content_part in agent_loop.run("What was my first question?"):
            if content_part: print(content_part, end='', flush=True)
        print("\n--- End of Stream ---")
        print(f"Transcript after clearing and new prompt:")
        for entry in agent_loop.transcript:
            print(f"  {entry['role']}: {entry['content'][:70]}...")


    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main_test())

import click
from pathlib import Path
import asyncio # Added asyncio
import os # Added for Windows asyncio policy

# Adjust imports based on how the package will be structured and run
try:
    from .models import AppConfig
    from .utils.config import load_config, save_config, CONFIG_DIR, INSTRUCTIONS_MD_NAME, DEFAULT_INSTRUCTIONS
    from .utils.default_providers import DEFAULT_PROVIDERS
    from .agent.agent_loop import AgentLoopPy
    from .tui.app import CodexTerminalApp # Added TUI App
except ImportError:
    # Fallback for cases where the script might be run directly and src is the CWD
    from models import AppConfig
    from utils.config import load_config, save_config, CONFIG_DIR, INSTRUCTIONS_MD_NAME, DEFAULT_INSTRUCTIONS
    from utils.default_providers import DEFAULT_PROVIDERS
    from agent.agent_loop import AgentLoopPy
    from tui.app import CodexTerminalApp # Added TUI App


VERSION = "codex-py 0.1.0" # Placeholder version

# Prepare INSTRUCTIONS_FILEPATH
INSTRUCTIONS_FILEPATH = CONFIG_DIR / INSTRUCTIONS_MD_NAME

# Context object to pass loaded config
class Context:
    def __init__(self):
        self.config: AppConfig = load_config()

@click.group(invoke_without_command=True)
@click.option('--model', '-m', 'cl_model', help="Specify the model to use.")
@click.option('--provider', '-p', 'cl_provider', help="Specify the provider to use.")
@click.option('--config', 'cl_config_flag', is_flag=True, help="Open the instructions file in your editor (prints path for now).")
@click.option('--version', 'cl_version_flag', is_flag=True, help="Print version and exit.")
@click.pass_context
def cli(ctx, cl_model, cl_provider, cl_config_flag, cl_version_flag):
    """A command-line interface for interacting with code generation models."""
    ctx.obj = Context() # Create and load config here

    if cl_version_flag:
        click.echo(VERSION)
        ctx.exit()

    if cl_config_flag:
        # In a real scenario, you'd use click.edit() or similar
        click.echo(f"Configuration instructions file: {INSTRUCTIONS_FILEPATH}")
        # Create instructions file if it doesn't exist
        if not INSTRUCTIONS_FILEPATH.exists():
            with open(INSTRUCTIONS_FILEPATH, 'w') as f:
                f.write(DEFAULT_INSTRUCTIONS)
            click.echo(f"Created default instructions file at {INSTRUCTIONS_FILEPATH}")
        ctx.exit() # Exit after showing config path or version

    # Apply CLI options to the loaded config (runtime only, not saved automatically)
    if cl_model:
        ctx.obj.config.model = cl_model
    if cl_provider:
        # TODO: Validate provider and ensure its config (API key, etc.) is loaded/handled
        ctx.obj.config.provider = cl_provider
        # Potentially update ctx.obj.config.api_key if provider changes
        if cl_provider in ctx.obj.config.providers:
            ctx.obj.config.api_key = ctx.obj.config.providers[cl_provider].api_key
        else:
            # Handle case where provider is not in known providers - maybe load a default or error
            click.echo(f"Warning: Provider '{cl_provider}' not found in configured providers. API key may be missing.", err=True)
            ctx.obj.config.api_key = None # Or try to get from env like OPENAI_API_KEY

    if ctx.invoked_subcommand is None:
        # If no subcommand is given, but other options were, they are handled above.
        # If only 'codex-py' is run without options, show help.
        if not (cl_model or cl_provider or cl_config_flag or cl_version_flag):
             click.echo(ctx.get_help())


@cli.command("execute")
@click.argument('prompt', required=False, default=None)
@click.option('--file', '-f', 'filepaths', multiple=True, type=click.Path(), help="Path to file(s) to include in the prompt context.")
@click.pass_context
async def execute_prompt(ctx, prompt: str, filepaths: tuple[str]): # Made async
    """Processes a prompt to generate and optionally apply code changes."""
    config: AppConfig = ctx.obj.config

    if not prompt and not filepaths:
        click.echo("Error: No prompt or file(s) provided. Please provide a prompt or use the -f/--file option.", err=True)
        click.echo(ctx.get_help())
        ctx.exit(1)
        
    final_prompt = prompt if prompt else ""

    if filepaths:
        for fp_str in filepaths:
            fp = Path(fp_str)
            if fp.exists() and fp.is_file():
                try:
                    with open(fp, 'r') as f_content:
                        final_prompt += f"\n\n--- Content of {fp.name} ---\n{f_content.read()}"
                except Exception as e:
                    click.echo(f"Error reading file {fp_str}: {e}", err=True)
            else:
                click.echo(f"Warning: File {fp_str} not found or is not a file.", err=True)

    if not final_prompt.strip():
        click.echo("Error: Prompt is empty after processing files.", err=True)
        ctx.exit(1)

    click.echo(f"Executing with:")
    click.echo(f"  Provider: {config.provider}")
    click.echo(f"  Model: {config.model}")
    click.echo(f"  API Key loaded: {'Yes' if config.api_key else 'No'}")
    click.echo(f"  Approval Mode: {config.approvalMode}")
    # click.echo(f"  Instructions (first 50 chars): {config.instructions[:50] if config.instructions else 'None'}...")
    # click.echo(f"  Prompt (first 100 chars): {final_prompt[:100]}...")
    
    if not config.api_key and config.provider not in ["ollama"]: # Ollama might not need API key
        click.echo(f"Error: API key for provider '{config.provider}' is missing. Please configure it.", err=True)
        ctx.exit(1)

    agent_loop = AgentLoopPy(app_config=config) 
    
    # Simulate some history for basic testing - only if API key is likely present
    # This is a temporary measure for manual verification
    if config.api_key and config.provider not in ["ollama"]: # Ollama might not need key
        click.echo("(Simulating pre-history for testing context...)")
        # Consume the async generator fully for these setup calls
        async def consume_gen(gen):
            async for _ in gen: pass

        await consume_gen(agent_loop.run("What is the main programming language used in the dotNet framework?"))
        await consume_gen(agent_loop.run("Can you give me a short example of a C# \"Hello World\"?"))
        click.echo("(Pre-history simulation complete.)")

    try:
        click.echo(f"\nUser (current prompt): \"{final_prompt[:150]}...\"")
        click.echo("Assistant: ", nl=False) # Print prefix for streaming
        full_response_parts = []
        async for content_part in agent_loop.run(final_prompt):
            if content_part:
                click.echo(content_part, nl=False)
                full_response_parts.append(content_part)
        click.echo() # Final newline after stream

        # Handle cases where the stream might have yielded error messages
        full_response = "".join(full_response_parts)
        if "OpenAI API Error" in full_response or "unexpected error" in full_response:
            # Error already printed by agent_loop's logging/callback, and yielded.
            # click.echo(f"\nError received from AI: {full_response}", err=True) # Avoid double printing if already handled by agent
            pass # Error message was part of the stream
        elif not full_response.strip():
            click.echo("No content received from the AI.", err=True)

    except Exception as e:
        click.echo(f"\nAn unexpected error occurred in CLI while processing agent response: {e}", err=True)
    finally:
        if agent_loop.on_loading: # Ensure loading indicator is turned off
            agent_loop.on_loading(False)


@cli.command("tui")
@click.pass_context
def launch_tui(ctx):
    """Launch the Textual User Interface."""
    # Config is already loaded in ctx.obj.config if needed by the TUI
    # For now, TUI app might load its own config or be passed parts of it.
    app = CodexTerminalApp()
    app.run()

# Potentially add other commands like 'configure', 'providers', etc. later

async def main_async(): # Renamed main to main_async and made it async
    # This makes the script runnable.
    # For package distribution, entry points in setup.py would point to this.
    if os.name == 'nt': # Required for Windows if using asyncio.run with Click
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    await cli(obj={}, auto_envvar_prefix='CODEX_PY') # obj={} is a default, auto_envvar_prefix for env var support

if __name__ == '__main__':
    # Click's default runner handles async functions correctly for commands.
    # If cli itself were async, we'd need asyncio.run(main_async()).
    # For now, cli is sync, and execute_prompt is async, which Click supports.
    cli(obj={}, auto_envvar_prefix='CODEX_PY')

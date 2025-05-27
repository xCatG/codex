import pytest
from click.testing import CliRunner
from unittest.mock import MagicMock, AsyncMock # AsyncMock for async functions

# Assuming PYTHONPATH is set up so that 'src' is accessible
from src.cli import cli
from src.models import AppConfig, ProviderInfo # For creating mock AppConfig
# AgentLoopPy and CodexTerminalApp are mocked at their source
# from src.agent.agent_loop import AgentLoopPy
# from src.tui.app import CodexTerminalApp

@pytest.fixture
def runner():
    return CliRunner()

@pytest.fixture
def mock_default_app_config():
    """Provides a default AppConfig instance for mocking load_config."""
    return AppConfig(
        model="default-model",
        provider="default-provider",
        api_key="sk-defaultkey",
        providers={
            "default-provider": ProviderInfo(name="Default Provider", api_key="sk-defaultkey", base_url="http://default.api"),
            "openai": ProviderInfo(name="OpenAI", api_key="sk-openai", base_url="https://api.openai.com/v1"),
            "test-provider": ProviderInfo(name="Test Provider", api_key="sk-test", base_url="http://test.api")
        }
    )

def test_cli_execute_basic_invocation(runner, mocker, mock_default_app_config):
    """Test basic invocation of `codex-py execute`."""
    mocker.patch('src.cli.load_config', return_value=mock_default_app_config)
    
    # Mock the AgentLoopPy.run method
    # Since AgentLoopPy.run is an async generator, its mock needs to reflect that.
    # For a simple return value test, we can make it an async function mock that returns a list of strings.
    # If the CLI iterates and prints, it will join them.
    async def mock_run_generator(*args, **kwargs):
        yield "Mocked "
        yield "AI "
        yield "response"

    mocker.patch('src.agent.agent_loop.AgentLoopPy.run', new=mock_run_generator)

    result = runner.invoke(cli, ['execute', 'test prompt'])
    
    assert result.exit_code == 0
    assert "Executing with:" in result.output
    assert f"Provider: {mock_default_app_config.provider}" in result.output
    assert f"Model: {mock_default_app_config.model}" in result.output
    assert "Assistant: Mocked AI response" in result.output.replace("\n", " ") # Handle newlines in output

def test_cli_version_option(runner):
    """Test `codex-py --version`."""
    # No need to mock load_config as --version exits early
    result = runner.invoke(cli, ['--version'])
    assert result.exit_code == 0
    assert "codex-py 0.1.0" in result.output # Assuming this is the version in cli.py

def test_cli_model_option(runner, mocker, mock_default_app_config):
    """Test `codex-py --model <model_name> execute`."""
    mock_load_config = mocker.patch('src.cli.load_config', return_value=mock_default_app_config)
    
    # Capture the AppConfig passed to AgentLoopPy constructor
    captured_config = None
    original_agent_loop_init = 'src.agent.agent_loop.AgentLoopPy.__init__'
    
    def mock_agent_init(self_agent, app_config):
        nonlocal captured_config
        captured_config = app_config
        # Call original __init__ if necessary, or just set required attributes
        self_agent.app_config = app_config 
        self_agent.oai_client = MagicMock() # Mock client
        self_agent.current_stream = None
        self_agent.canceled = False
        self_agent.on_item_callback = None
        self_agent.on_loading = None


    mocker.patch(original_agent_loop_init, side_effect=mock_agent_init, autospec=True)
    
    async def mock_run_generator(*args, **kwargs):
        yield "Model test response"
    mocker.patch('src.agent.agent_loop.AgentLoopPy.run', new=mock_run_generator)

    test_model_name = "gpt-test-cli"
    result = runner.invoke(cli, ['--model', test_model_name, 'execute', 'test prompt for model option'])
    
    assert result.exit_code == 0
    assert mock_load_config.called # Ensure load_config was called
    
    # Check that the config passed to AgentLoopPy was updated
    assert captured_config is not None
    assert captured_config.model == test_model_name
    # Also check that the original mock_default_app_config's model is different,
    # to ensure the CLI option is what caused the change.
    assert mock_default_app_config.model != test_model_name
    assert f"Model: {test_model_name}" in result.output # CLI should echo the used model

def test_cli_tui_command(runner, mocker, mock_default_app_config):
    """Test `codex-py tui` command."""
    mocker.patch('src.cli.load_config', return_value=mock_default_app_config)
    mock_tui_app_run = mocker.patch('src.tui.app.CodexTerminalApp.run')

    result = runner.invoke(cli, ['tui'])
    
    assert result.exit_code == 0
    mock_tui_app_run.assert_called_once()

def test_cli_execute_no_prompt_or_file(runner, mocker, mock_default_app_config):
    """Test `codex-py execute` with no prompt or file, expecting error."""
    mocker.patch('src.cli.load_config', return_value=mock_default_app_config)
    # No need to mock AgentLoopPy.run as it should exit before that

    result = runner.invoke(cli, ['execute'])
    
    assert result.exit_code == 1 # Should exit with error
    assert "Error: No prompt or file(s) provided." in result.output

def test_cli_config_option_creates_instructions(runner, mocker, tmp_path):
    """Test `codex-py --config` creates instructions file if not exists."""
    # Use tmp_path for CONFIG_DIR to isolate file system changes
    mock_config_dir = tmp_path / ".codex-py"
    mocker.patch('src.cli.CONFIG_DIR', mock_config_dir)
    
    # Ensure instructions file does not exist initially
    instructions_file = mock_config_dir / "instructions.md"
    assert not instructions_file.exists()

    result = runner.invoke(cli, ['--config'])
    
    assert result.exit_code == 0
    assert f"Configuration instructions file: {instructions_file}" in result.output
    assert instructions_file.exists()
    assert "Created default instructions file" in result.output
    with open(instructions_file, 'r') as f:
        content = f.read()
        from src.utils.config import DEFAULT_INSTRUCTIONS # Get the default content
        assert content == DEFAULT_INSTRUCTIONS

def test_cli_config_option_prints_existing_instructions_path(runner, mocker, tmp_path):
    """Test `codex-py --config` prints path to existing instructions file."""
    mock_config_dir = tmp_path / ".codex-py"
    mock_config_dir.mkdir()
    instructions_file = mock_config_dir / "instructions.md"
    custom_instructions = "My custom instructions."
    with open(instructions_file, 'w') as f:
        f.write(custom_instructions)
    
    mocker.patch('src.cli.CONFIG_DIR', mock_config_dir)
    
    result = runner.invoke(cli, ['--config'])
    
    assert result.exit_code == 0
    assert f"Configuration instructions file: {instructions_file}" in result.output
    assert "Created default instructions file" not in result.output # Should not recreate
    with open(instructions_file, 'r') as f:
        content = f.read()
        assert content == custom_instructions # Ensure it wasn't overwritten


if __name__ == "__main__":
    pytest.main([__file__])

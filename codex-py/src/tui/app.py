from textual.app import App, ComposeResult

# Relative imports
try:
    from .screens.chat_screen import ChatScreen
    from ..utils.config import load_config, AppConfig # Adjusted import
except ImportError:
    # Fallback for different execution contexts (e.g., running app.py directly)
    from screens.chat_screen import ChatScreen
    # This relative import might fail if src is not on path for direct run
    from utils.config import load_config, AppConfig


class CodexTerminalApp(App):
    """A Textual app for Codex-Py."""

    TITLE = "Codex-Py"
    # CSS_PATH = "app.css" 

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            self.app_config: AppConfig = load_config()
            if not self.app_config.api_key and self.app_config.provider not in ["ollama"]:
                 print(f"Warning: API key for provider '{self.app_config.provider}' is missing.")
        except Exception as e:
            print(f"Error loading AppConfig in CodexTerminalApp: {e}")
            # Fallback to a default/empty AppConfig if loading fails,
            # or handle more gracefully (e.g., push an error screen).
            self.app_config = AppConfig() # Minimal AppConfig

    def on_mount(self) -> None:
        """Called when the app is first mounted."""
        self.push_screen(ChatScreen())

if __name__ == '__main__':
    # This allows running the TUI directly for development/testing
    # Ensure PYTHONPATH includes the parent directory of 'src' for imports like 'from ..utils.config'
    # Example: If codex-py is the root, run from codex-py: python -m src.tui.app
    app = CodexTerminalApp()
    app.run()

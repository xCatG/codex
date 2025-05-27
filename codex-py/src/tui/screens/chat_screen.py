from textual.screen import Screen
from textual.widgets import Header, Footer, Static, Input
from textual.containers import VerticalScroll # Renamed to avoid conflict
from textual.app import ComposeResult
from textual.css.query import DOMQuery

# Adjust relative imports based on expected execution context
try:
    from ...agent.agent_loop import AgentLoopPy
    from ...models import AppConfig # For type hinting if needed, app.app_config is main source
except ImportError:
    # Fallback for different execution contexts (e.g., running screen directly for testing)
    # This might require specific PYTHONPATH adjustments if running outside 'python -m src.cli tui'
    from agent.agent_loop import AgentLoopPy # Assuming PYTHONPATH includes src
    from models import AppConfig


class ChatScreen(Screen):
    """A simple chat screen for Codex-Py TUI, integrating AgentLoopPy."""

    BINDINGS = [
        ("escape", "app.quit", "Quit")
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.agent_loop: AgentLoopPy | None = None
        self.messages_view: VerticalScroll | None = None
        self.chat_input: Input | None = None

    def on_mount(self) -> None:
        """Called when the screen is first mounted."""
        # Access AppConfig from the app instance
        app_config = self.app.app_config
        if not app_config:
            # Handle case where AppConfig might not be loaded (e.g. error during app init)
            # You could display an error message on screen or log and disable input.
            self.query_one("#chat_input", Input).disabled = True
            self.query_one("#messages_view", VerticalScroll).mount(Static("Error: AppConfig not loaded. Chat disabled."))
            return

        self.agent_loop = AgentLoopPy(app_config=app_config)
        
        # Get references to widgets (safer than querying every time)
        self.messages_view = self.query_one("#messages_view", VerticalScroll)
        self.chat_input = self.query_one("#chat_input", Input)
        self.chat_input.focus() # Focus input on screen load

    def compose(self) -> ComposeResult:
        """Create child widgets for the screen."""
        yield Header()
        # Using VerticalScroll directly as its own class is fine.
        # If you had a custom class named VerticalScroll, then aliasing import would be needed.
        yield VerticalScroll(
            Static("Welcome to Codex-Py TUI Chat!", classes="welcome-message"),
            id="messages_view"
        )
        yield Input(placeholder="Type your message here...", id="chat_input")
        yield Footer()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle user input submission."""
        if not self.agent_loop or not self.messages_view or not self.chat_input:
            return # Should not happen if on_mount completed successfully

        user_input_text = event.value
        if not user_input_text.strip():
            return # Ignore empty input

        # Clear the input field
        self.chat_input.value = ""

        # Display user's message
        user_message_widget = Static(f"You: {user_input_text}", classes="user-message")
        self.messages_view.mount(user_message_widget)
        self.messages_view.scroll_end(animate=False)

        # Create and display placeholder for assistant's response
        assistant_response_widget = Static("Assistant: Thinking...", classes="assistant-message thinking")
        self.messages_view.mount(assistant_response_widget)
        self.messages_view.scroll_end(animate=False)

        # Run the agent and stream the response
        current_response_text = "Assistant: "
        try:
            async for content_part in self.agent_loop.run(user_input_text):
                if content_part:
                    current_response_text += content_part
                    # Update the assistant's message widget with the new content part
                    # Ensure we are not updating a potentially removed widget if user quits fast
                    if assistant_response_widget.is_mounted:
                         assistant_response_widget.remove_class("thinking") # Remove thinking class on first token
                         assistant_response_widget.update(current_response_text)
                    self.messages_view.scroll_end(animate=False) # Auto-scroll
            
            # Final update in case the stream was empty but successful (unlikely for LLMs)
            if assistant_response_widget.is_mounted and assistant_response_widget.has_class("thinking"):
                assistant_response_widget.remove_class("thinking")
                if current_response_text == "Assistant: ": # No actual content streamed
                    assistant_response_widget.update("Assistant: (No response content)")


        except Exception as e:
            # Handle errors during agent execution, update the widget
            error_message = f"Assistant: Error - {str(e)}"
            if assistant_response_widget.is_mounted:
                assistant_response_widget.remove_class("thinking")
                assistant_response_widget.update(error_message)
            self.messages_view.scroll_end(animate=False)
            # Optionally, log the full error for debugging
            # self.app.log.error(f"Agent execution error: {e}")

if __name__ == '__main__':
    # This is a simple way to test the ChatScreen independently
    # It requires a mock or minimal App and AppConfig setup.
    from textual.app import App
    from src.models import AppConfig # Assuming models.py is in src/
    
    class TestChatScreenApp(App):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            # Minimal config for testing screen structure; API calls won't work without real config
            self.app_config = AppConfig(model="test", provider="test") 

        def on_mount(self) -> None:
            self.push_screen(ChatScreen())
    
    app = TestChatScreenApp()
    app.run()

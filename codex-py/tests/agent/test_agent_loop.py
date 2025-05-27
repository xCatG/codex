import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

# Assuming PYTHONPATH is set up so that 'src' is accessible
from src.agent.agent_loop import AgentLoopPy
from src.models import AppConfig, ProviderInfo

# Mock stream chunk and choice structure for OpenAI client
class MockDelta:
    def __init__(self, content):
        self.content = content

class MockChoice:
    def __init__(self, content):
        self.delta = MockDelta(content)

class MockStreamChunk:
    def __init__(self, content=None):
        self.choices = [MockChoice(content)] if content else []

@pytest.fixture
def mock_app_config():
    """Provides a basic AppConfig for AgentLoopPy."""
    return AppConfig(
        model="test-model",
        provider="test-provider",
        api_key="sk-testkey",
        instructions="You are a test assistant.",
        providers={
            "test-provider": ProviderInfo(name="Test Provider", api_key="sk-testkey")
        }
    )

@pytest.fixture
def mock_openai_client():
    """Mocks the OpenAI client and its streaming response."""
    mock_client = MagicMock()
    # The create method itself needs to be an async function
    # and it needs to return an async iterable (async generator)
    
    async def mock_completion_stream(*args, **kwargs):
        # Simulate receiving a few chunks of data
        # This will be the response for EACH call to agent_loop.run() in these tests
        yield MockStreamChunk("Test ")
        yield MockStreamChunk("response")
        yield MockStreamChunk(".")

    mock_client.chat.completions.create = AsyncMock(return_value=mock_completion_stream())
    return mock_client


@pytest.mark.asyncio # Pytest marker for async tests
async def test_agent_loop_transcript_update(mock_app_config, mock_openai_client):
    """Test that transcript is updated correctly after user and assistant turns."""
    
    with patch('src.utils.openai_client_factory.create_openai_client', return_value=mock_openai_client):
        agent_loop = AgentLoopPy(app_config=mock_app_config)

    # --- First interaction ---
    prompt1 = "test prompt 1"
    expected_response1 = "Test response."
    
    # Consume the async generator from run()
    response_parts1 = []
    async for part in agent_loop.run(prompt1):
        response_parts1.append(part)
    full_response1 = "".join(response_parts1)

    assert full_response1 == expected_response1
    assert len(agent_loop.transcript) == 2 # user prompt, assistant response
    assert agent_loop.transcript[0] == {"role": "user", "content": prompt1}
    assert agent_loop.transcript[1] == {"role": "assistant", "content": expected_response1}

    # Check arguments passed to OpenAI client for the first call
    call_args_first = mock_openai_client.chat.completions.create.call_args_list[0]
    messages_first_call = call_args_first.kwargs['messages']
    assert len(messages_first_call) == 2 # system, user1
    assert messages_first_call[0]['role'] == 'system'
    assert messages_first_call[1]['role'] == 'user'
    assert messages_first_call[1]['content'] == prompt1


    # --- Second interaction ---
    prompt2 = "test prompt 2"
    expected_response2 = "Test response." # Mock stream yields the same response

    # Re-assign the mock stream for the second call, as an async generator can only be consumed once.
    async def mock_completion_stream_second(*args, **kwargs):
        yield MockStreamChunk("Test ")
        yield MockStreamChunk("response")
        yield MockStreamChunk(".")
    mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_completion_stream_second())

    response_parts2 = []
    async for part in agent_loop.run(prompt2):
        response_parts2.append(part)
    full_response2 = "".join(response_parts2)

    assert full_response2 == expected_response2
    assert len(agent_loop.transcript) == 4 # user1, assistant1, user2, assistant2
    assert agent_loop.transcript[2] == {"role": "user", "content": prompt2}
    assert agent_loop.transcript[3] == {"role": "assistant", "content": expected_response2}

    # Check arguments passed to OpenAI client for the second call
    # Ensure the history from the first interaction was included
    call_args_second = mock_openai_client.chat.completions.create.call_args_list[1]
    messages_second_call = call_args_second.kwargs['messages']
    
    # Expected: system, user1, assistant1, user2
    assert len(messages_second_call) == 4 
    assert messages_second_call[0]['role'] == 'system'
    assert messages_second_call[1]['role'] == 'user'
    assert messages_second_call[1]['content'] == prompt1
    assert messages_second_call[2]['role'] == 'assistant'
    assert messages_second_call[2]['content'] == expected_response1
    assert messages_second_call[3]['role'] == 'user'
    assert messages_second_call[3]['content'] == prompt2


@pytest.mark.asyncio
async def test_agent_loop_clear_history(mock_app_config, mock_openai_client):
    """Test the clear_history method."""
    with patch('src.utils.openai_client_factory.create_openai_client', return_value=mock_openai_client):
        agent_loop = AgentLoopPy(app_config=mock_app_config)

    # Add some items to history
    prompt1 = "history prompt"
    async for _ in agent_loop.run(prompt1): # Consume the generator
        pass 
    
    assert len(agent_loop.transcript) == 2 # user, assistant

    agent_loop.clear_history()
    assert len(agent_loop.transcript) == 0
    assert agent_loop.transcript == []

@pytest.mark.asyncio
async def test_agent_loop_run_with_on_item_callback(mock_app_config, mock_openai_client):
    """Test that on_item_callback is called during streaming."""
    callback_received_items = []
    def my_callback(item: str):
        callback_received_items.append(item)

    with patch('src.utils.openai_client_factory.create_openai_client', return_value=mock_openai_client):
        agent_loop = AgentLoopPy(app_config=mock_app_config, on_item_callback=my_callback)

    async for _ in agent_loop.run("callback test"):
        pass
    
    assert len(callback_received_items) == 3 # "Test ", "response", "."
    assert "".join(callback_received_items) == "Test response."

@pytest.mark.asyncio
async def test_agent_loop_cancellation_during_stream(mock_app_config, mock_openai_client):
    """Test cancellation during an active stream."""
    
    # Mock stream that yields indefinitely until cancelled or some condition
    async def long_stream(*args, **kwargs):
        count = 0
        while True: # Simulate a very long stream
            count += 1
            yield MockStreamChunk(f"Part{count} ")
            await asyncio.sleep(0.001) # Small delay to allow cancellation to interject

    mock_openai_client.chat.completions.create = AsyncMock(return_value=long_stream())

    with patch('src.utils.openai_client_factory.create_openai_client', return_value=mock_openai_client):
        agent_loop = AgentLoopPy(app_config=mock_app_config)

    received_parts = []
    max_parts_before_cancel = 3
    
    try:
        async for part in agent_loop.run("long stream test"):
            received_parts.append(part)
            if len(received_parts) >= max_parts_before_cancel:
                agent_loop.cancel() # Request cancellation
    except Exception as e:
        pytest.fail(f"Stream consumption failed during cancellation test: {e}")

    assert len(received_parts) <= max_parts_before_cancel + 1 # Allow for one extra part due to async nature
    assert agent_loop.canceled
    # The final assistant message in transcript should only contain received parts
    assert len(agent_loop.transcript) == 2 # user, assistant
    assert agent_loop.transcript[1]["role"] == "assistant"
    assert agent_loop.transcript[1]["content"] == "".join(received_parts)


# --- Tests for Specific API Errors ---

@pytest.mark.asyncio
async def test_agent_loop_handles_rate_limit_error(mock_app_config, mock_openai_client):
    mock_openai_client.chat.completions.create = AsyncMock(side_effect=RateLimitError("Rate limited", response=MagicMock(), body=None))
    with patch('src.utils.openai_client_factory.create_openai_client', return_value=mock_openai_client):
        agent_loop = AgentLoopPy(app_config=mock_app_config)
    
    error_message = ""
    async for part in agent_loop.run("test prompt"):
        error_message += part
    
    assert "Rate Limit Exceeded" in error_message
    assert "Rate limited" in error_message
    assert len(agent_loop.transcript) == 2 # user, assistant (with error message)
    assert agent_loop.transcript[1]["role"] == "assistant"
    assert "Rate Limit Exceeded" in agent_loop.transcript[1]["content"]

@pytest.mark.asyncio
async def test_agent_loop_handles_authentication_error(mock_app_config, mock_openai_client):
    mock_openai_client.chat.completions.create = AsyncMock(side_effect=AuthenticationError("Invalid API key", response=MagicMock(), body=None))
    with patch('src.utils.openai_client_factory.create_openai_client', return_value=mock_openai_client):
        agent_loop = AgentLoopPy(app_config=mock_app_config)

    error_message = ""
    async for part in agent_loop.run("test prompt"):
        error_message += part

    assert "Authentication Error" in error_message
    assert "Invalid API key" in error_message
    assert agent_loop.transcript[1]["content"] == error_message

@pytest.mark.asyncio
async def test_agent_loop_handles_not_found_error(mock_app_config, mock_openai_client):
    mock_openai_client.chat.completions.create = AsyncMock(side_effect=NotFoundError("Model not found", response=MagicMock(), body=None))
    with patch('src.utils.openai_client_factory.create_openai_client', return_value=mock_openai_client):
        agent_loop = AgentLoopPy(app_config=mock_app_config)

    error_message = ""
    async for part in agent_loop.run("test prompt"):
        error_message += part

    assert "Model not found or resource does not exist" in error_message
    assert "Model not found" in error_message
    assert agent_loop.transcript[1]["content"] == error_message

@pytest.mark.asyncio
async def test_agent_loop_handles_api_connection_error(mock_app_config, mock_openai_client):
    mock_openai_client.chat.completions.create = AsyncMock(side_effect=APIConnectionError("Connection failed"))
    with patch('src.utils.openai_client_factory.create_openai_client', return_value=mock_openai_client):
        agent_loop = AgentLoopPy(app_config=mock_app_config)

    error_message = ""
    async for part in agent_loop.run("test prompt"):
        error_message += part

    assert "Connection Error" in error_message
    assert "Connection failed" in error_message
    assert agent_loop.transcript[1]["content"] == error_message

@pytest.mark.asyncio
async def test_agent_loop_handles_api_status_error(mock_app_config, mock_openai_client, mocker):
    # Need to mock the response object for APIStatusError
    mock_response = mocker.Mock()
    mock_response.status_code = 500
    mock_openai_client.chat.completions.create = AsyncMock(side_effect=APIStatusError("Server error", response=mock_response, body=None))
    
    with patch('src.utils.openai_client_factory.create_openai_client', return_value=mock_openai_client):
        agent_loop = AgentLoopPy(app_config=mock_app_config)

    error_message = ""
    async for part in agent_loop.run("test prompt"):
        error_message += part

    assert "API Error (Status 500)" in error_message
    assert "Server error" in error_message
    assert agent_loop.transcript[1]["content"] == error_message

@pytest.mark.asyncio
async def test_agent_loop_successful_streaming_concatenation(mock_app_config, mock_openai_client):
    """ This test was implicitly covered by test_agent_loop_transcript_update,
        but this one focuses solely on the streamed output concatenation.
    """
    # mock_openai_client.chat.completions.create is already set up in the fixture
    # to return an async generator yielding "Test ", "response", "."
    
    with patch('src.utils.openai_client_factory.create_openai_client', return_value=mock_openai_client):
        agent_loop = AgentLoopPy(app_config=mock_app_config)

    response_parts = []
    async for part in agent_loop.run("stream test"):
        response_parts.append(part)
    full_response = "".join(response_parts)

    assert full_response == "Test response."
    # Also check the transcript for the assistant's message
    assert len(agent_loop.transcript) == 2
    assert agent_loop.transcript[0]["role"] == "user"
    assert agent_loop.transcript[0]["content"] == "stream test"
    assert agent_loop.transcript[1]["role"] == "assistant"
    assert agent_loop.transcript[1]["content"] == "Test response."


if __name__ == "__main__":
    pytest.main([__file__])

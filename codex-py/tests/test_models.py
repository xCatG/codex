import pytest
from pydantic import ValidationError

# Assuming PYTHONPATH is set up so that 'codex_py.src' is accessible
# This might require running pytest with PYTHONPATH=. if 'codex_py' is the root dir
# or PYTHONPATH=../ if tests are run from the 'tests' dir directly and 'codex_py' is parent.
# For now, using the path as specified in the task.
from src.models import (
    ProviderInfo,
    StoredConfig,
    AppConfig,
    FileOperation,
    EditedFiles
)

def test_provider_info_instantiation():
    """Test successful ProviderInfo instantiation."""
    provider = ProviderInfo(name="TestProvider", base_url="http://localhost", env_key="TEST_KEY", api_key="xyz")
    assert provider.name == "TestProvider"
    assert provider.base_url == "http://localhost"
    assert provider.env_key == "TEST_KEY"
    assert provider.api_key == "xyz"

    provider_minimal = ProviderInfo(name="MinimalProvider")
    assert provider_minimal.name == "MinimalProvider"
    assert provider_minimal.base_url is None
    assert provider_minimal.env_key is None
    assert provider_minimal.api_key is None

def test_stored_config_instantiation():
    """Test successful StoredConfig instantiation."""
    config = StoredConfig(
        model="gpt-test",
        provider="test_provider",
        approvalMode="manual",
        instructions="Test instructions.",
        providers={"test_provider": ProviderInfo(name="TestProvider")},
        default_provider="test_provider"
    )
    assert config.model == "gpt-test"
    assert config.provider == "test_provider"
    assert config.approvalMode == "manual"
    assert config.providers["test_provider"].name == "TestProvider"

    config_default = StoredConfig()
    assert config_default.model is None # Default is None as per model
    assert config_default.approvalMode == "auto" # Default from model
    assert config_default.providers == {}

def test_app_config_instantiation():
    """Test successful AppConfig instantiation (inherits from StoredConfig)."""
    app_conf = AppConfig(
        model="app-gpt",
        provider="app_provider",
        api_key="app_key_123"
    )
    assert app_conf.model == "app-gpt"
    assert app_conf.provider == "app_provider"
    assert app_conf.api_key == "app_key_123"
    assert app_conf.approvalMode == "auto" # Default from StoredConfig

def test_file_operation_instantiation():
    """Test successful FileOperation instantiation."""
    op_create = FileOperation(operation="create", path="test.txt", content="Hello")
    assert op_create.operation == "create"
    assert op_create.path == "test.txt"
    assert op_create.content == "Hello"

    op_rename = FileOperation(operation="rename", path="old.txt", new_path="new.txt")
    assert op_rename.operation == "rename"
    assert op_rename.new_path == "new.txt"

def test_edited_files_instantiation():
    """Test successful EditedFiles instantiation."""
    op1 = FileOperation(operation="create", path="a.txt", content="a")
    edited = EditedFiles(
        operations=[op1],
        reasoning="Test reasoning",
        summary="Test summary"
    )
    assert len(edited.operations) == 1
    assert edited.operations[0].path == "a.txt"
    assert edited.reasoning == "Test reasoning"

# --- Validation Error Tests ---

def test_stored_config_invalid_approval_mode():
    """Test StoredConfig for ValidationError with invalid approvalMode."""
    with pytest.raises(ValidationError) as excinfo:
        StoredConfig(approvalMode="invalid_mode")
    assert "approvalMode" in str(excinfo.value)
    # Example check for specific error message if desired:
    # assert "Input should be 'auto', 'manual' or 'none'" in str(excinfo.value)

def test_file_operation_invalid_operation_type():
    """Test FileOperation for ValidationError with invalid operation type."""
    with pytest.raises(ValidationError) as excinfo:
        FileOperation(operation="modify", path="test.txt") # 'modify' is not a valid literal
    assert "operation" in str(excinfo.value)

def test_file_operation_missing_fields_for_rename():
    """Test FileOperation for missing new_path on rename."""
    # Pydantic v2 automatically checks for required fields based on literals if using discriminated unions.
    # For simple models as defined, new_path is Optional, so this won't raise unless logic is added.
    # If the model was:
    # if operation == "rename": assert new_path is not None (via validator)
    # then this test would be relevant.
    # For now, this test shows that it *doesn't* raise for the current model.
    try:
        FileOperation(operation="rename", path="old.txt")
        # assert True # Or no assertion needed if we expect it not to fail
    except ValidationError:
        pytest.fail("FileOperation with operation='rename' should not require new_path at Pydantic level with current model")

def test_provider_info_missing_name():
    """Test ProviderInfo for ValidationError if name is missing."""
    with pytest.raises(ValidationError) as excinfo:
        ProviderInfo(base_url="http://localhost") # name is not optional
    assert "'name' is a required field" in str(excinfo.value) or "Field required" in str(excinfo.value) # Pydantic v1 vs v2
    

if __name__ == "__main__":
    # This allows running pytest on this file directly for quick checks
    # (though typically you'd run `pytest` from the project root)
    pytest.main([__file__])

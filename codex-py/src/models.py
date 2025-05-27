from typing import List, Optional, Dict, Literal
from pydantic import BaseModel, Field

class ProviderInfo(BaseModel):
    name: str
    base_url: Optional[str] = None
    env_key: Optional[str] = None
    api_key: Optional[str] = None  # Added to store resolved API key

class StoredConfig(BaseModel):
    model: Optional[str] = None
    provider: Optional[str] = None
    approvalMode: Optional[Literal["auto", "manual", "none"]] = Field(default="auto", alias="approvalMode")
    instructions: Optional[str] = None
    providers: Optional[Dict[str, ProviderInfo]] = {}
    default_provider: Optional[str] = None

class AppConfig(StoredConfig):
    api_key: Optional[str] = None # For the current provider
    # other app-specific fields can be added here
    # We will merge StoredConfig and environment variables into this

class FileOperation(BaseModel):
    operation: Literal["create", "edit", "delete", "rename"]
    path: str
    new_path: Optional[str] = None  # For rename operations
    content: Optional[str] = None   # For create/edit operations

class EditedFiles(BaseModel):
    operations: List[FileOperation] = []
    reasoning: Optional[str] = None
    summary: Optional[str] = None
    warnings: Optional[List[str]] = []
    raw_response: Optional[str] = None

# Example Usage (can be removed later)
if __name__ == "__main__":
    # ProviderInfo Example
    openai_provider = ProviderInfo(name="OpenAI", base_url="https://api.openai.com/v1", env_key="OPENAI_API_KEY")
    print(openai_provider)

    # StoredConfig Example
    stored_conf = StoredConfig(model="gpt-4", provider="openai", approvalMode="manual")
    print(stored_conf)

    # AppConfig Example (inherits from StoredConfig)
    app_conf = AppConfig(model="gpt-3.5-turbo", provider="openai", api_key="sk-...")
    print(app_conf)

    # FileOperation Example
    create_op = FileOperation(operation="create", path="new_file.txt", content="Hello world")
    edit_op = FileOperation(operation="edit", path="existing_file.txt", content="Updated content")
    delete_op = FileOperation(operation="delete", path="old_file.txt")
    rename_op = FileOperation(operation="rename", path="current_name.txt", new_path="new_name.txt")
    print(create_op)
    print(edit_op)
    print(delete_op)
    print(rename_op)

    # EditedFiles Example
    edited_set = EditedFiles(
        operations=[create_op, edit_op],
        reasoning="Created one file and edited another based on requirements.",
        summary="File modifications complete."
    )
    print(edited_set)

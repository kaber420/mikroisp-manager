import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from app.utils.env_manager import update_env_file, get_env_context

TEST_ENV = ".env.test"

def setup():
    with open(TEST_ENV, "w") as f:
        f.write("EXISTING_VAR=old_value\n")
        f.write("# This is a comment\n")
        f.write("KEEP_ME=safe\n")

def cleanup():
    if os.path.exists(TEST_ENV):
        os.remove(TEST_ENV)

def test_update():
    print("Testing update_env_file...")
    setup()
    
    updates = {
        "EXISTING_VAR": "new_value",
        "NEW_VAR": "created"
    }
    
    update_env_file(updates, TEST_ENV)
    
    # Verify content
    context = get_env_context(TEST_ENV)
    
    assert context["EXISTING_VAR"] == "new_value", "Failed to update existing var"
    assert context["NEW_VAR"] == "created", "Failed to create new var"
    assert context["KEEP_ME"] == "safe", "Failed to preserve existing var"
    
    # Verify file structure (comment preservation)
    with open(TEST_ENV, "r") as f:
        content = f.read()
        assert "# This is a comment" in content, "Failed to preserve comments"
        
    print("✅ All tests passed!")
    cleanup()

if __name__ == "__main__":
    test_update()

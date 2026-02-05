import os
import re

def update_env_file(updates: dict[str, str], env_path: str = ".env"):
    """
    Updates the .env file with the provided key-value pairs.
    Preserves comments and existing structure.
    Adds new keys if they don't exist.
    """
    if not os.path.exists(env_path):
        # Create new file if it doesn't exist
        with open(env_path, "w") as f:
            for key, value in updates.items():
                f.write(f'{key}="{value}"\n')
        return

    with open(env_path, "r") as f:
        lines = f.readlines()

    new_lines = []
    processed_keys = set()

    for line in lines:
        # Check if line contains a key we want to update
        # Regex looks for KEY= or KEY="value" or KEY='value'
        match = re.match(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=', line)
        
        if match:
            key = match.group(1)
            if key in updates:
                # Update this line
                value = updates[key]
                new_lines.append(f'{key}="{value}"\n')
                processed_keys.add(key)
            else:
                # Keep existing line
                new_lines.append(line)
        else:
            # Keep comments/blank lines
            new_lines.append(line)

    # Append new keys that weren't found in the file
    for key, value in updates.items():
        if key not in processed_keys:
            # Add a newline before appending new keys if the file ended without one
            if new_lines and not new_lines[-1].endswith('\n'):
                new_lines.append('\n')
            new_lines.append(f'{key}="{value}"\n')

    with open(env_path, "w") as f:
        f.writelines(new_lines)

def get_env_context(env_path: str = ".env") -> dict[str, str]:
    """
    Reads the .env file and returns a dictionary of current values.
    This is useful for populating the UI with current file-based settings.
    """
    context = {}
    if not os.path.exists(env_path):
        return context

    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            
            # Simple parsing: KEY=VALUE
            # Remove quotes if present
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                value = parts[1].strip()
                
                # Strip wrapping quotes
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                
                context[key] = value
    return context

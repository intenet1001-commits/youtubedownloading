#!/usr/bin/env python3
"""
Environment Variable Loader
Safely loads environment variables from .env file
"""

import os
from pathlib import Path


def load_env_file(env_path=None):
    """Load environment variables from .env file"""
    if env_path is None:
        env_path = Path('.env')
    else:
        env_path = Path(env_path)
    
    if not env_path.exists():
        return False, f".env file not found at {env_path}"
    
    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Remove quotes if present
                    if (value.startswith('"') and value.endswith('"')) or \
                       (value.startswith("'") and value.endswith("'")):
                        value = value[1:-1]
                    
                    os.environ[key] = value
        
        return True, f"Environment variables loaded from {env_path}"
        
    except Exception as e:
        return False, f"Error loading .env file: {e}"


def check_required_vars():
    """Check if all required environment variables are set"""
    required_vars = ['GITHUB_TOKEN', 'GITHUB_REPO_URL']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        return False, f"Missing required environment variables: {', '.join(missing_vars)}"
    
    return True, "All required environment variables are set"


if __name__ == "__main__":
    # Load environment variables
    success, message = load_env_file()
    print(f"Load .env: {message}")
    
    if success:
        # Check required variables
        success, message = check_required_vars()
        print(f"Check vars: {message}")
        
        # Show loaded variables (without showing token value)
        token = os.getenv('GITHUB_TOKEN', '')
        repo_url = os.getenv('GITHUB_REPO_URL', '')
        
        print(f"GITHUB_TOKEN: {'*' * 20 if token else 'NOT SET'}")
        print(f"GITHUB_REPO_URL: {repo_url}")
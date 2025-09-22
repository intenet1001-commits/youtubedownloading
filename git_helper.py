#!/usr/bin/env python3
"""
Secure Git Auto-Push Helper Module
Handles automated Git operations with secure token management
"""

import os
import subprocess
import datetime
from pathlib import Path
import json


class GitHelper:
    def __init__(self, repo_path=None):
        """
        Initialize GitHelper with repository path
        
        Args:
            repo_path: Path to git repository (defaults to current directory)
        """
        self.repo_path = Path(repo_path) if repo_path else Path.cwd()
        self.github_token = os.getenv('GITHUB_TOKEN')
        self.repo_url = os.getenv('GITHUB_REPO_URL', 'https://github.com/intenet1001-commits/youtubedownloading')
        
    def check_git_repo(self):
        """Check if current directory is a git repository"""
        git_dir = self.repo_path / '.git'
        return git_dir.exists()
    
    def check_dependencies(self):
        """Check if git is available and token is set"""
        try:
            result = subprocess.run(['git', '--version'], 
                                  capture_output=True, text=True, check=True)
            git_available = True
            git_version = result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            git_available = False
            git_version = None
            
        return {
            'git_available': git_available,
            'git_version': git_version,
            'token_set': bool(self.github_token),
            'repo_exists': self.check_git_repo()
        }
    
    def get_git_status(self):
        """Get current git status"""
        try:
            # Check if there are changes
            result = subprocess.run(['git', 'status', '--porcelain'], 
                                  cwd=self.repo_path, capture_output=True, text=True)
            has_changes = bool(result.stdout.strip())
            
            # Get current branch
            branch_result = subprocess.run(['git', 'branch', '--show-current'], 
                                         cwd=self.repo_path, capture_output=True, text=True)
            current_branch = branch_result.stdout.strip()
            
            # Get last commit info
            commit_result = subprocess.run(['git', 'log', '-1', '--oneline'], 
                                         cwd=self.repo_path, capture_output=True, text=True)
            last_commit = commit_result.stdout.strip()
            
            return {
                'has_changes': has_changes,
                'current_branch': current_branch,
                'last_commit': last_commit,
                'changes': result.stdout.strip().split('\n') if has_changes else []
            }
            
        except subprocess.CalledProcessError as e:
            return {'error': f'Git status error: {e}'}
    
    def add_all_changes(self):
        """Add all changes to git staging area"""
        try:
            subprocess.run(['git', 'add', '.'], 
                          cwd=self.repo_path, check=True)
            return True, "All changes added to staging area"
        except subprocess.CalledProcessError as e:
            return False, f"Failed to add changes: {e}"
    
    def create_commit(self, message=None):
        """Create a commit with automatic message if none provided"""
        if not message:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            message = f"Auto-commit: {timestamp}"
        
        try:
            subprocess.run(['git', 'commit', '-m', message], 
                          cwd=self.repo_path, check=True)
            return True, f"Commit created: {message}"
        except subprocess.CalledProcessError as e:
            return False, f"Failed to create commit: {e}"
    
    def push_to_remote(self, branch=None):
        """Push changes to remote repository"""
        if not self.github_token:
            return False, "GitHub token not set. Please set GITHUB_TOKEN environment variable."
        
        if not branch:
            status = self.get_git_status()
            branch = status.get('current_branch', 'main')
        
        try:
            # Set up authenticated remote URL
            auth_url = self.repo_url.replace('https://', f'https://{self.github_token}@')
            
            # Push to remote
            subprocess.run(['git', 'push', auth_url, branch], 
                          cwd=self.repo_path, check=True, 
                          capture_output=True)
            
            return True, f"Successfully pushed to {branch}"
            
        except subprocess.CalledProcessError as e:
            return False, f"Failed to push: {e}"
    
    def auto_push(self, commit_message=None, log_callback=None):
        """
        Perform complete auto-push workflow:
        1. Check for changes
        2. Add all changes
        3. Commit with message
        4. Push to remote
        """
        def log(message):
            if log_callback:
                log_callback(message)
            else:
                print(message)
        
        # Check dependencies
        deps = self.check_dependencies()
        if not deps['git_available']:
            return False, "Git is not available"
        if not deps['token_set']:
            return False, "GitHub token not set"
        if not deps['repo_exists']:
            return False, "Not a git repository"
        
        log("🔍 Checking git status...")
        
        # Get current status
        status = self.get_git_status()
        if 'error' in status:
            return False, status['error']
        
        if not status['has_changes']:
            log("ℹ️  No changes to commit")
            return True, "No changes to push"
        
        log(f"📝 Found {len(status['changes'])} changes")
        
        # Add changes
        log("➕ Adding changes...")
        success, result = self.add_all_changes()
        if not success:
            return False, result
        log(result)
        
        # Create commit
        log("💾 Creating commit...")
        success, result = self.create_commit(commit_message)
        if not success:
            return False, result
        log(result)
        
        # Push to remote
        log("🚀 Pushing to remote...")
        success, result = self.push_to_remote()
        if not success:
            return False, result
        log(result)
        
        log("✅ Auto-push completed successfully!")
        return True, "Auto-push completed successfully"
    
    def setup_remote(self):
        """Set up remote repository if not already configured"""
        try:
            # Check if remote origin exists
            result = subprocess.run(['git', 'remote', 'get-url', 'origin'], 
                                  cwd=self.repo_path, capture_output=True, text=True)
            
            if result.returncode != 0:
                # Add remote origin
                subprocess.run(['git', 'remote', 'add', 'origin', self.repo_url], 
                              cwd=self.repo_path, check=True)
                return True, "Remote origin added"
            else:
                return True, "Remote origin already configured"
                
        except subprocess.CalledProcessError as e:
            return False, f"Failed to setup remote: {e}"


def create_env_example():
    """Create example .env file for token configuration"""
    env_example = """# GitHub Configuration
# Create a Personal Access Token at: https://github.com/settings/tokens
# Required permissions: repo (Full control of private repositories)

GITHUB_TOKEN=your_github_token_here
GITHUB_REPO_URL=https://github.com/intenet1001-commits/youtubedownloading

# Optional: Set default commit message template
DEFAULT_COMMIT_MESSAGE=Auto-commit: Application updates
"""
    
    env_path = Path('.env.example')
    with open(env_path, 'w') as f:
        f.write(env_example)
    
    return env_path


if __name__ == "__main__":
    # Load environment variables first
    from load_env import load_env_file
    load_env_file()
    
    # Test the GitHelper functionality
    git_helper = GitHelper()
    
    print("=== Git Helper Test ===")
    
    # Check dependencies
    deps = git_helper.check_dependencies()
    print(f"Git available: {deps['git_available']}")
    print(f"Token set: {deps['token_set']}")
    print(f"Git repo: {deps['repo_exists']}")
    
    if deps['git_available'] and deps['repo_exists']:
        # Get status
        status = git_helper.get_git_status()
        print(f"Has changes: {status.get('has_changes', False)}")
        print(f"Current branch: {status.get('current_branch', 'unknown')}")
        
        # Create example env file
        env_file = create_env_example()
        print(f"Created example env file: {env_file}")
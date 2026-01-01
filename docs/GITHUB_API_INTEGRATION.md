# GitHub API Integration Guide

## Overview
This guide shows how to push code to external GitHub repositories using the GitHub API directly, without relying on platform-specific integrations.

---

## 🎯 Recommended Approach: PyGithub Library

### Installation
```bash
pip install PyGithub
```

### Why PyGithub?
- ✅ Simple, high-level API
- ✅ Handles all low-level Git operations
- ✅ Active maintenance and community support
- ✅ Comprehensive documentation
- ✅ Already have Python environment

---

## 📝 Implementation Examples

### 1. Basic Setup

```python
from github import Github
import os

class GitHubCodePusher:
    """Push code to GitHub repositories via API"""
    
    def __init__(self, access_token: str):
        """
        Initialize GitHub client
        
        Args:
            access_token: GitHub Personal Access Token
        """
        self.github = Github(access_token)
        self.user = self.github.get_user()
    
    def get_or_create_repo(self, repo_name: str, private: bool = True):
        """Get existing repo or create new one"""
        try:
            repo = self.user.get_repo(repo_name)
            print(f"✅ Found existing repo: {repo_name}")
            return repo
        except:
            print(f"📦 Creating new repo: {repo_name}")
            repo = self.user.create_repo(
                name=repo_name,
                private=private,
                auto_init=True,  # Create with README
                description="Auto-generated repository"
            )
            return repo
```

### 2. Push Single File

```python
def push_file(self, repo_name: str, file_path: str, content: str, 
              commit_message: str, branch: str = "main"):
    """
    Push a single file to repository
    
    Args:
        repo_name: Repository name
        file_path: Path in repo (e.g., "src/main.py")
        content: File content
        commit_message: Commit message
        branch: Target branch
    
    Returns:
        Commit SHA
    """
    repo = self.github.get_user().get_repo(repo_name)
    
    try:
        # Try to get existing file
        file = repo.get_contents(file_path, ref=branch)
        
        # Update existing file
        result = repo.update_file(
            path=file.path,
            message=commit_message,
            content=content,
            sha=file.sha,
            branch=branch
        )
        print(f"✅ Updated {file_path}")
        
    except:
        # File doesn't exist, create it
        result = repo.create_file(
            path=file_path,
            message=commit_message,
            content=content,
            branch=branch
        )
        print(f"✅ Created {file_path}")
    
    return result['commit'].sha
```

### 3. Push Multiple Files in Single Commit

```python
def push_multiple_files(self, repo_name: str, files: dict, 
                       commit_message: str, branch: str = "main"):
    """
    Push multiple files in a single commit
    
    Args:
        repo_name: Repository name
        files: Dict of {file_path: content}
        commit_message: Commit message
        branch: Target branch
    
    Returns:
        Commit SHA
    
    Example:
        files = {
            "README.md": "# My Project",
            "src/main.py": "print('Hello')",
            "config.json": '{"version": "1.0"}'
        }
    """
    repo = self.github.get_user().get_repo(repo_name)
    
    # Get current branch reference
    ref = repo.get_git_ref(f"heads/{branch}")
    base_commit = repo.get_git_commit(ref.object.sha)
    base_tree = base_commit.tree
    
    # Create blobs for each file
    element_list = []
    for file_path, content in files.items():
        blob = repo.create_git_blob(content, "utf-8")
        element = {
            "path": file_path,
            "mode": "100644",  # Regular file
            "type": "blob",
            "sha": blob.sha
        }
        element_list.append(element)
    
    # Create tree
    tree = repo.create_git_tree(element_list, base_tree)
    
    # Create commit
    commit = repo.create_git_commit(
        message=commit_message,
        tree=tree,
        parents=[base_commit]
    )
    
    # Update reference
    ref.edit(commit.sha)
    
    print(f"✅ Committed {len(files)} files: {commit.sha[:8]}")
    return commit.sha
```

### 4. Push Entire Directory

```python
import os
from pathlib import Path

def push_directory(self, repo_name: str, local_dir: str, 
                   repo_path: str = "", commit_message: str = None,
                   branch: str = "main"):
    """
    Push entire local directory to repository
    
    Args:
        repo_name: Repository name
        local_dir: Local directory path
        repo_path: Path in repo (empty for root)
        commit_message: Commit message (auto-generated if None)
        branch: Target branch
    
    Returns:
        Commit SHA
    """
    files = {}
    
    # Read all files from directory
    for root, dirs, filenames in os.walk(local_dir):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        
        for filename in filenames:
            # Skip hidden files
            if filename.startswith('.'):
                continue
            
            local_path = os.path.join(root, filename)
            
            # Calculate relative path
            rel_path = os.path.relpath(local_path, local_dir)
            
            # Add repo_path prefix if provided
            if repo_path:
                repo_file_path = f"{repo_path}/{rel_path}"
            else:
                repo_file_path = rel_path
            
            # Convert Windows paths to Unix
            repo_file_path = repo_file_path.replace('\\', '/')
            
            # Read file content
            try:
                with open(local_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                files[repo_file_path] = content
            except UnicodeDecodeError:
                # Binary file, read as bytes and encode as base64
                with open(local_path, 'rb') as f:
                    import base64
                    content = base64.b64encode(f.read()).decode('utf-8')
                files[repo_file_path] = content
    
    if not commit_message:
        commit_message = f"Push {len(files)} files from {local_dir}"
    
    return self.push_multiple_files(repo_name, files, commit_message, branch)
```

### 5. Clone Repository to Local

```python
def clone_repo(self, repo_name: str, local_path: str, branch: str = "main"):
    """
    Download repository contents to local directory
    
    Args:
        repo_name: Repository name
        local_path: Local directory to save files
        branch: Branch to clone
    """
    repo = self.github.get_user().get_repo(repo_name)
    
    # Get all contents recursively
    contents = repo.get_contents("", ref=branch)
    
    os.makedirs(local_path, exist_ok=True)
    
    while contents:
        file_content = contents.pop(0)
        
        if file_content.type == "dir":
            # Directory: get its contents
            contents.extend(repo.get_contents(file_content.path, ref=branch))
        else:
            # File: download it
            file_path = os.path.join(local_path, file_content.path)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'wb') as f:
                f.write(file_content.decoded_content)
            
            print(f"✅ Downloaded {file_content.path}")
    
    print(f"✅ Cloned {repo_name} to {local_path}")
```

---

## 🔐 Authentication Setup

### 1. Generate Personal Access Token

1. Go to https://github.com/settings/tokens
2. Click "Generate new token" → "Generate new token (classic)"
3. Give it a name (e.g., "Lockbay Bot")
4. Select scopes:
   - ✅ `repo` (Full control of private repositories)
   - ✅ `workflow` (Update GitHub Action workflows)
5. Click "Generate token"
6. **Copy the token immediately** (you won't see it again)

### 2. Store Token Securely

**Using Environment Variables:**
```bash
# In .env file (never commit this!)
GITHUB_ACCESS_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
```

**In Python:**
```python
import os
from dotenv import load_dotenv

load_dotenv()
token = os.getenv('GITHUB_ACCESS_TOKEN')
pusher = GitHubCodePusher(token)
```

**Using Replit Secrets (if on Replit):**
```python
import os
token = os.environ.get('GITHUB_ACCESS_TOKEN')
```

---

## 📊 Complete Usage Example

```python
#!/usr/bin/env python3
"""
Example: Backup Lockbay bot code to GitHub
"""
import os
from github import Github

# Initialize
token = os.getenv('GITHUB_ACCESS_TOKEN')
pusher = GitHubCodePusher(token)

# Example 1: Push single configuration file
pusher.push_file(
    repo_name="lockbay-config-backup",
    file_path="config/settings.json",
    content='{"version": "1.0", "updated": "2025-10-22"}',
    commit_message="Update configuration"
)

# Example 2: Push multiple files at once
files = {
    "README.md": "# Lockbay Bot\nEscrow bot for secure transactions",
    "handlers/escrow.py": open("handlers/escrow.py").read(),
    "services/payment.py": open("services/payment.py").read(),
    "config.py": open("config.py").read()
}

pusher.push_multiple_files(
    repo_name="lockbay-backup",
    files=files,
    commit_message="Backup core handlers and services"
)

# Example 3: Backup entire project directory
pusher.push_directory(
    repo_name="lockbay-full-backup",
    local_dir=".",
    repo_path="",
    commit_message="Full project backup - October 2025"
)

print("✅ All backups completed successfully!")
```

---

## ⚡ Advanced Features

### Create Branch and Pull Request

```python
def create_feature_branch(self, repo_name: str, branch_name: str, 
                         base_branch: str = "main"):
    """Create a new branch from base branch"""
    repo = self.github.get_user().get_repo(repo_name)
    
    # Get base branch SHA
    base = repo.get_branch(base_branch)
    
    # Create new branch
    repo.create_git_ref(
        ref=f"refs/heads/{branch_name}",
        sha=base.commit.sha
    )
    print(f"✅ Created branch: {branch_name}")

def create_pull_request(self, repo_name: str, title: str, body: str,
                       head_branch: str, base_branch: str = "main"):
    """Create pull request"""
    repo = self.github.get_user().get_repo(repo_name)
    
    pr = repo.create_pull(
        title=title,
        body=body,
        head=head_branch,
        base=base_branch
    )
    
    print(f"✅ Created PR #{pr.number}: {pr.html_url}")
    return pr
```

### Automated Daily Backups

```python
from datetime import datetime

def daily_backup(self):
    """Automated daily backup"""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    
    # Create timestamped branch
    branch_name = f"backup-{timestamp}"
    self.create_feature_branch("lockbay-backup", branch_name)
    
    # Push current state
    files_to_backup = {
        "handlers/": "handlers/",
        "services/": "services/",
        "utils/": "utils/",
        "config.py": "config.py"
    }
    
    # ... backup logic ...
    
    print(f"✅ Daily backup completed: {branch_name}")
```

---

## 🚨 Error Handling

```python
from github import GithubException

try:
    pusher.push_file(...)
except GithubException as e:
    if e.status == 401:
        print("❌ Authentication failed - check your token")
    elif e.status == 404:
        print("❌ Repository not found")
    elif e.status == 403:
        print("❌ Permission denied - check token scopes")
    elif e.status == 409:
        print("❌ Conflict - file might be locked")
    else:
        print(f"❌ GitHub API error: {e.status} - {e.data}")
except Exception as e:
    print(f"❌ Unexpected error: {e}")
```

---

## 🔧 Alternative: Raw REST API

If you don't want to use PyGithub:

```python
import requests
import base64
import json

class GitHubAPIClient:
    """Direct REST API client"""
    
    def __init__(self, token: str):
        self.token = token
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
    
    def create_or_update_file(self, owner: str, repo: str, 
                             path: str, content: str, message: str):
        """Create or update file via REST API"""
        url = f"{self.base_url}/repos/{owner}/{repo}/contents/{path}"
        
        # Check if file exists
        response = requests.get(url, headers=self.headers)
        
        # Prepare payload
        payload = {
            "message": message,
            "content": base64.b64encode(content.encode()).decode()
        }
        
        if response.status_code == 200:
            # File exists, include SHA for update
            payload["sha"] = response.json()["sha"]
        
        # Create or update
        response = requests.put(url, headers=self.headers, json=payload)
        
        if response.status_code in [200, 201]:
            print(f"✅ Success: {path}")
            return response.json()
        else:
            print(f"❌ Failed: {response.status_code}")
            print(response.json())
```

---

## 📋 Best Practices

1. **Rate Limits**
   - Authenticated: 5,000 requests/hour
   - Monitor: Check `X-RateLimit-Remaining` header
   - Handle: Implement exponential backoff on 403

2. **Security**
   - ✅ Never commit tokens to code
   - ✅ Use environment variables
   - ✅ Rotate tokens regularly
   - ✅ Use minimal required scopes

3. **Performance**
   - ✅ Batch multiple files in single commit
   - ✅ Use conditional requests (ETags)
   - ✅ Implement caching where appropriate

4. **Error Handling**
   - ✅ Handle network failures gracefully
   - ✅ Retry on transient errors
   - ✅ Log all operations for debugging

---

## 🔗 Resources

- **PyGithub Documentation**: https://pygithub.readthedocs.io/
- **GitHub REST API**: https://docs.github.com/en/rest
- **Personal Access Tokens**: https://github.com/settings/tokens
- **API Rate Limits**: https://docs.github.com/en/rest/overview/rate-limits-for-the-rest-api

---

## 📝 Next Steps

1. Install PyGithub: `pip install PyGithub`
2. Generate GitHub token with `repo` scope
3. Store token in environment variable
4. Test with simple file push
5. Implement automated backups

**Your code is ready to push to GitHub! 🚀**

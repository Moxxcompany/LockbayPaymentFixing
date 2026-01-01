#!/usr/bin/env python3
"""
GitHub Code Pusher - Example Implementation
Push code to GitHub repositories via API
"""
from github import Github
import os
from typing import Dict, Optional


class GitHubCodePusher:
    """Push code to GitHub repositories using PyGithub"""
    
    def __init__(self, access_token: str):
        """
        Initialize GitHub client
        
        Args:
            access_token: GitHub Personal Access Token
        """
        self.github = Github(access_token)
        self.user = self.github.get_user()
        print(f"✅ Authenticated as: {self.user.login}")
    
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
                auto_init=True,
                description="Auto-generated repository"
            )
            return repo
    
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
            file = repo.get_contents(file_path, ref=branch)
            result = repo.update_file(
                path=file.path,
                message=commit_message,
                content=content,
                sha=file.sha,
                branch=branch
            )
            print(f"✅ Updated {file_path}")
        except:
            result = repo.create_file(
                path=file_path,
                message=commit_message,
                content=content,
                branch=branch
            )
            print(f"✅ Created {file_path}")
        
        return result['commit'].sha
    
    def push_multiple_files(self, repo_name: str, files: Dict[str, str], 
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
        """
        repo = self.github.get_user().get_repo(repo_name)
        
        ref = repo.get_git_ref(f"heads/{branch}")
        base_commit = repo.get_git_commit(ref.object.sha)
        base_tree = base_commit.tree
        
        element_list = []
        for file_path, content in files.items():
            blob = repo.create_git_blob(content, "utf-8")
            element = {
                "path": file_path,
                "mode": "100644",
                "type": "blob",
                "sha": blob.sha
            }
            element_list.append(element)
        
        tree = repo.create_git_tree(element_list, base_tree)
        commit = repo.create_git_commit(
            message=commit_message,
            tree=tree,
            parents=[base_commit]
        )
        ref.edit(commit.sha)
        
        print(f"✅ Committed {len(files)} files: {commit.sha[:8]}")
        return commit.sha


def main():
    """Example usage"""
    # Get token from environment
    token = os.getenv('GITHUB_ACCESS_TOKEN')
    
    if not token:
        print("❌ GITHUB_ACCESS_TOKEN not set")
        print("   Set it with: export GITHUB_ACCESS_TOKEN=ghp_your_token")
        return
    
    # Initialize
    pusher = GitHubCodePusher(token)
    
    # Example: Push multiple files
    files = {
        "README.md": "# My Project\nCreated via GitHub API",
        "src/main.py": "print('Hello from GitHub API!')",
        "config.json": '{"version": "1.0"}'
    }
    
    try:
        repo = pusher.get_or_create_repo("test-api-repo", private=True)
        
        commit_sha = pusher.push_multiple_files(
            repo_name="test-api-repo",
            files=files,
            commit_message="Initial commit via API"
        )
        
        print(f"\n✅ Success! Commit: {commit_sha}")
        print(f"🔗 View at: https://github.com/{pusher.user.login}/test-api-repo")
        
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()

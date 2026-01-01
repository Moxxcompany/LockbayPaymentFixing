#!/usr/bin/env python3
"""
Quick Deploy Script for LockBay
Rapid deployment for development changes with minimal prompts
"""

import os
import sys
import subprocess
from datetime import datetime

def quick_deploy():
    """Quick deployment with auto-generated commit message"""
    
    print("⚡ Quick Deploy - LockBay")
    print("=" * 30)
    
    # Check if we're in a git repo
    if not os.path.exists(".git"):
        print("❌ Not a git repository")
        return False
    
    try:
        # Check for changes
        result = subprocess.run(
            ["git", "status", "--porcelain"], 
            capture_output=True, 
            text=True, 
            check=True
        )
        
        if not result.stdout.strip():
            print("✅ No changes to deploy")
            
            # Check if we need to pull
            try:
                branch_result = subprocess.run(
                    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                    capture_output=True, text=True, check=True
                )
                branch = branch_result.stdout.strip()
                
                subprocess.run(["git", "fetch"], check=True)
                
                behind_result = subprocess.run([
                    "git", "rev-list", "--count", f"HEAD..origin/{branch}"
                ], capture_output=True, text=True, check=True)
                
                behind_count = int(behind_result.stdout.strip())
                
                if behind_count > 0:
                    print(f"📥 Pulling {behind_count} new commits from GitHub...")
                    subprocess.run(["git", "pull"], check=True)
                    print("✅ Repository updated")
                
            except Exception as e:
                print(f"⚠️  Could not check for updates: {e}")
                pass  # Ignore fetch/pull errors
                
            return True
        
        # Count changes
        lines = result.stdout.strip().split('\n')
        change_count = len([line for line in lines if line])
        
        print(f"📦 Found {change_count} changed file(s)")
        
        # Stage all changes
        print("📦 Staging all changes...")
        subprocess.run(["git", "add", "."], check=True)
        
        # Generate commit message
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        commit_message = f"Quick update: {change_count} files - {timestamp}"
        
        # Allow custom message
        custom_message = input(f"💬 Commit message (Enter for: '{commit_message}'): ").strip()
        if custom_message:
            commit_message = custom_message
        
        # Commit
        print(f"💾 Committing: {commit_message}")
        subprocess.run(["git", "commit", "-m", commit_message], check=True)
        
        # Get current branch
        branch_result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, check=True
        )
        branch = branch_result.stdout.strip()
        
        # Push
        print(f"🚀 Pushing to GitHub (branch: {branch})...")
        subprocess.run(["git", "push", "origin", branch], check=True)
        
        print("✅ Quick deploy completed!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Git command failed: {e}")
        return False
    except KeyboardInterrupt:
        print("\n⚠️ Deploy cancelled by user")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("""
Quick Deploy Script for LockBay

This script provides rapid deployment for development changes:
- Automatically stages all changes
- Generates timestamp-based commit messages  
- Pushes to current branch
- Minimal prompts for speed

Usage:
  python quick-deploy.py        # Run quick deployment
  python quick-deploy.py --help # Show this help

For more control, use the main deploy.py script instead.
        """)
        return
    
    success = quick_deploy()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
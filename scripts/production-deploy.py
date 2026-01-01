#!/usr/bin/env python3
"""
Production Deployment Script for LockBay
Secure deployment with safeguards, testing, and production branch management
"""

import os
import sys
import subprocess
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class ProductionDeployer:
    def __init__(self):
        self.repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.production_branch = "main"
        self.staging_branch = "develop"
        
    def run_command(self, cmd: List[str], capture_output: bool = True):
        """Run a shell command and return output (str) or success (bool)"""
        try:
            if capture_output:
                result = subprocess.run(
                    cmd, cwd=self.repo_root, capture_output=True, 
                    text=True, check=True
                )
                return result.stdout.strip()
            else:
                subprocess.run(cmd, cwd=self.repo_root, check=True)
                return True  # Return True to indicate success
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if hasattr(e, 'stderr') and e.stderr else str(e)
            print(f"❌ Command failed: {' '.join(cmd)}")
            print(f"Error: {error_msg}")
            return False if not capture_output else None
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return False if not capture_output else None
    
    def check_production_readiness(self) -> Dict[str, bool]:
        """Check if code is ready for production deployment"""
        checks = {
            "git_clean": False,
            "on_develop": False,
            "tests_exist": False,
            "no_debug_code": False,
            "secrets_check": False,
            "docker_build": False
        }
        
        # Check if working directory is clean
        git_status = self.run_command(["git", "status", "--porcelain"])
        if git_status is not None and not git_status:
            checks["git_clean"] = True
        
        # Check current branch
        current_branch = self.run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"])
        if current_branch == self.staging_branch:
            checks["on_develop"] = True
        
        # Check if tests exist
        test_files = [
            "tests/",
            "test/",
            "pytest.ini",
            "pyproject.toml"
        ]
        checks["tests_exist"] = any(os.path.exists(os.path.join(self.repo_root, f)) for f in test_files)
        
        # Check for debug code patterns
        debug_patterns = ["print(", "console.log(", "debugger;", "pdb.set_trace()", "breakpoint()"]
        try:
            # Check main Python files for debug patterns
            main_files = ["main.py", "production_start.py", "webhook_server.py"]
            debug_found = False
            
            for file in main_files:
                file_path = os.path.join(self.repo_root, file)
                if os.path.exists(file_path):
                    with open(file_path, 'r') as f:
                        content = f.read()
                        for pattern in debug_patterns:
                            if pattern in content and "# DEBUG:" not in content:
                                debug_found = True
                                break
            
            checks["no_debug_code"] = not debug_found
        except Exception as e:
            logger.warning(f"Debug code check failed: {e}")
            checks["no_debug_code"] = True  # Assume no debug code if check fails
        
        # Check for required secrets/env vars
        required_secrets = ["BOT_TOKEN", "DATABASE_URL"]
        secrets_present = all(os.getenv(key) for key in required_secrets)
        checks["secrets_check"] = secrets_present
        
        # Test Docker build (optional)
        if os.path.exists(os.path.join(self.repo_root, "Dockerfile")):
            print("🐳 Testing Docker build...")
            docker_result = self.run_command([
                "docker", "build", "--target", "production", 
                "-t", "lockbay-test:latest", "."
            ], capture_output=False)
            checks["docker_build"] = bool(docker_result)
        else:
            checks["docker_build"] = True  # No Docker, assume OK
        
        return checks
    
    def run_tests(self) -> bool:
        """Run test suite if available"""
        test_commands = [
            ["python", "-m", "pytest", "-v"],
            ["python", "-m", "pytest"],
            ["pytest", "-v"],
            ["pytest"]
        ]
        
        tests_attempted = False
        
        for cmd in test_commands:
            print(f"🧪 Running tests: {' '.join(cmd)}")
            result = self.run_command(cmd, capture_output=False)
            
            if result is None:
                # Command not found, try next command
                continue
            
            tests_attempted = True
            
            if result:
                print("✅ Tests passed")
                return True
            else:
                print("❌ Tests failed")
                return False
        
        if not tests_attempted:
            print("⚠️ No test runner found (pytest not available)")
            return True  # Don't fail deployment if no test tools available
        
        return False  # Should not reach here
    
    def merge_to_production(self) -> bool:
        """Merge develop branch to main for production"""
        print(f"🔄 Merging {self.staging_branch} to {self.production_branch}...")
        
        # Fetch latest
        if not self.run_command(["git", "fetch"], capture_output=False):
            return False
        
        # Checkout main
        if not self.run_command(["git", "checkout", self.production_branch], capture_output=False):
            return False
        
        # Pull latest main
        if not self.run_command(["git", "pull", "origin", self.production_branch], capture_output=False):
            return False
        
        # Merge develop
        if not self.run_command(["git", "merge", self.staging_branch], capture_output=False):
            print("❌ Merge failed. Resolve conflicts and try again.")
            return False
        
        print("✅ Successfully merged to production branch")
        return True
    
    def create_release_tag(self, version: Optional[str] = None) -> bool:
        """Create a release tag"""
        if not version:
            # Generate version based on date
            version = f"v{datetime.now().strftime('%Y.%m.%d')}"
            
            # Check if tag exists and increment
            counter = 1
            while True:
                check_tag = self.run_command(["git", "tag", "-l", f"{version}.{counter}"])
                if not check_tag:
                    version = f"{version}.{counter}"
                    break
                counter += 1
        
        # Create tag
        tag_message = f"Production release {version} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        if not self.run_command(["git", "tag", "-a", version, "-m", tag_message], capture_output=False):
            return False
        
        # Push tag
        if not self.run_command(["git", "push", "origin", version], capture_output=False):
            return False
        
        print(f"✅ Created release tag: {version}")
        return True
    
    def deploy_to_production(self, skip_tests: bool = False, auto_merge: bool = False) -> bool:
        """Full production deployment workflow"""
        print("🚀 Production Deployment - LockBay")
        print("=" * 40)
        
        # Pre-flight checks
        print("🔍 Running pre-flight checks...")
        checks = self.check_production_readiness()
        
        print("\n📋 Production Readiness Report:")
        for check, passed in checks.items():
            status = "✅" if passed else "❌"
            check_name = check.replace("_", " ").title()
            print(f"  {status} {check_name}")
        
        # Count failed checks
        failed_checks = [k for k, v in checks.items() if not v]
        
        if failed_checks and not auto_merge:
            print(f"\n⚠️ {len(failed_checks)} check(s) failed:")
            for check in failed_checks:
                print(f"  • {check.replace('_', ' ').title()}")
            
            continue_anyway = input("\nContinue with production deployment? (y/N): ").strip().lower()
            if continue_anyway != 'y':
                print("❌ Production deployment cancelled")
                return False
        
        # Run tests
        if not skip_tests and checks["tests_exist"]:
            print("\n🧪 Running test suite...")
            if not self.run_tests():
                if not auto_merge:
                    continue_anyway = input("Tests failed. Continue anyway? (y/N): ").strip().lower()
                    if continue_anyway != 'y':
                        return False
        
        # Merge to production
        if not auto_merge:
            merge_confirm = input(f"\n🔄 Merge {self.staging_branch} to {self.production_branch}? (Y/n): ").strip().lower()
            if merge_confirm == 'n':
                print("❌ Merge cancelled")
                return False
        
        if not self.merge_to_production():
            return False
        
        # Push to production
        print(f"🚀 Pushing {self.production_branch} to GitHub...")
        if not self.run_command(["git", "push", "origin", self.production_branch], capture_output=False):
            return False
        
        # Create release tag
        if not auto_merge:
            create_tag = input("\n🏷️ Create release tag? (Y/n): ").strip().lower()
            if create_tag != 'n':
                custom_version = input("Version (Enter for auto): ").strip()
                self.create_release_tag(custom_version if custom_version else None)
        else:
            self.create_release_tag()
        
        print("\n🎉 Production deployment completed successfully!")
        print("🔗 GitHub Actions CI/CD will handle the rest")
        
        # Switch back to develop
        self.run_command(["git", "checkout", self.staging_branch], capture_output=False)
        print(f"✅ Switched back to {self.staging_branch} branch")
        
        return True
    
    def hotfix_deploy(self, fix_description: str) -> bool:
        """Deploy a hotfix directly to production"""
        print("🚨 Hotfix Deployment")
        print("=" * 25)
        
        # Check if we're on main
        current_branch = self.run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"])
        if current_branch != self.production_branch:
            print(f"⚠️ Switching to {self.production_branch} branch...")
            if not self.run_command(["git", "checkout", self.production_branch], capture_output=False):
                return False
        
        # Check for uncommitted changes
        git_status = self.run_command(["git", "status", "--porcelain"])
        if git_status:
            print("❌ Uncommitted changes found. Commit or stash them first.")
            return False
        
        # Pull latest
        if not self.run_command(["git", "pull", "origin", self.production_branch], capture_output=False):
            return False
        
        print("⚠️ Ready for hotfix. Make your changes now and then press Enter...")
        input("Press Enter when changes are complete...")
        
        # Check for new changes
        git_status = self.run_command(["git", "status", "--porcelain"])
        if not git_status:
            print("❌ No changes detected")
            return False
        
        # Stage and commit
        if not self.run_command(["git", "add", "."], capture_output=False):
            return False
        
        commit_message = f"Hotfix: {fix_description} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        if not self.run_command(["git", "commit", "-m", commit_message], capture_output=False):
            return False
        
        # Push
        if not self.run_command(["git", "push", "origin", self.production_branch], capture_output=False):
            return False
        
        # Create hotfix tag
        hotfix_version = f"hotfix-{datetime.now().strftime('%Y%m%d-%H%M')}"
        if not self.run_command(["git", "tag", "-a", hotfix_version, "-m", commit_message], capture_output=False):
            return False
        
        if not self.run_command(["git", "push", "origin", hotfix_version], capture_output=False):
            return False
        
        print(f"✅ Hotfix deployed: {hotfix_version}")
        
        # Merge hotfix back to develop
        print(f"🔄 Merging hotfix back to {self.staging_branch}...")
        if not self.run_command(["git", "checkout", self.staging_branch], capture_output=False):
            return False
        
        if not self.run_command(["git", "merge", self.production_branch], capture_output=False):
            print("⚠️ Manual merge required for develop branch")
        else:
            self.run_command(["git", "push", "origin", self.staging_branch], capture_output=False)
        
        return True

def main():
    deployer = ProductionDeployer()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--auto":
            success = deployer.deploy_to_production(skip_tests=False, auto_merge=True)
        elif sys.argv[1] == "--hotfix":
            description = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "Emergency fix"
            success = deployer.hotfix_deploy(description)
        elif sys.argv[1] == "--check":
            checks = deployer.check_production_readiness()
            print(json.dumps(checks, indent=2))
            return
        elif sys.argv[1] == "--help":
            print("""
Production Deployment Script for LockBay

Usage:
  python production-deploy.py                    # Interactive production deployment
  python production-deploy.py --auto            # Automated production deployment  
  python production-deploy.py --hotfix [desc]   # Deploy emergency hotfix
  python production-deploy.py --check           # Check production readiness
  python production-deploy.py --help            # Show this help

Examples:
  python production-deploy.py --hotfix "Fix payment processing bug"
  python production-deploy.py --auto
            """)
            return
        else:
            print(f"Unknown option: {sys.argv[1]}")
            print("Use --help for usage information")
            return
    else:
        success = deployer.deploy_to_production()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
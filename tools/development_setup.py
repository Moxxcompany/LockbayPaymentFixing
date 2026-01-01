"""Development Tools and Local Setup Utilities"""

import logging
import os
import subprocess
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import psutil

logger = logging.getLogger(__name__)


class DevelopmentEnvironment:
    """Development environment setup and management"""

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root).resolve()
        self.config = self.load_dev_config()

    def load_dev_config(self) -> Dict[str, Any]:
        """Load development configuration"""
        config_file = self.project_root / "dev_config.json"

        default_config = {
            "python_version": "3.11",
            "node_version": "18",
            "services": {
                "postgres": {
                    "port": 5432,
                    "database": "lockbay_dev",
                    "user": "postgres",
                    "password": "dev_password",
                },
                "redis": {"port": 6379, "password": "dev_redis_password"},
                "bot": {"port": 5000, "debug": True, "auto_reload": True},
            },
            "environment_variables": {
                "ENVIRONMENT": "development",
                "DEBUG_MODE": "true",
                "LOG_LEVEL": "DEBUG",
            },
            "development_features": {
                "hot_reload": True,
                "debug_toolbar": True,
                "mock_external_apis": True,
                "test_webhooks": True,
            },
        }

        if config_file.exists():
            try:
                with open(config_file) as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
            except Exception as e:
                logger.warning(f"Failed to load dev config: {e}")

        return default_config

    def save_dev_config(self):
        """Save development configuration"""
        config_file = self.project_root / "dev_config.json"
        try:
            with open(config_file, "w") as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save dev config: {e}")

    def setup_environment(self) -> bool:
        """Setup complete development environment"""
        try:
            logger.info("🚀 Setting up development environment...")

            # Create necessary directories
            self.create_dev_directories()

            # Setup environment variables
            self.setup_environment_variables()

            # Setup git hooks
            self.setup_git_hooks()

            # Generate development certificates
            self.generate_dev_certificates()

            # Create test data
            self.create_test_data()

            # Setup IDE configuration
            self.setup_ide_config()

            logger.info("✅ Development environment setup complete!")
            return True

        except Exception as e:
            logger.error(f"❌ Development setup failed: {e}")
            return False

    def create_dev_directories(self):
        """Create development directories"""
        directories = [
            "logs",
            "backups",
            "tmp",
            "test_data",
            "ssl/dev",
            ".vscode",
            "scripts/dev",
            "docs/dev",
        ]

        for directory in directories:
            dir_path = self.project_root / directory
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory: {directory}")

    def setup_environment_variables(self):
        """Setup development environment variables"""
        env_file = self.project_root / ".env.development"

        env_vars = {
            **self.config["environment_variables"],
            "DATABASE_URL": f"postgresql://{self.config['services']['postgres']['user']}:{self.config['services']['postgres']['password']}@localhost:{self.config['services']['postgres']['port']}/{self.config['services']['postgres']['database']}",
            "REDIS_URL": f"redis://:{self.config['services']['redis']['password']}@localhost:{self.config['services']['redis']['port']}/0",
            "BOT_TOKEN": "test_bot_token_for_development",
            "WEBHOOK_SECRET_TOKEN": "dev_webhook_secret",
            "NGROK_TUNNEL": "https://dev.lockbay.ngrok.io",
        }

        env_content = "\n".join([f"{key}={value}" for key, value in env_vars.items()])

        with open(env_file, "w") as f:
            f.write(env_content)

        logger.info("✅ Environment variables setup complete")

    def setup_git_hooks(self):
        """Setup git pre-commit hooks"""
        hooks_dir = self.project_root / ".git/hooks"

        if not hooks_dir.exists():
            logger.warning("Git repository not found, skipping hooks setup")
            return

        pre_commit_hook = hooks_dir / "pre-commit"

        hook_script = """#!/bin/bash
# Pre-commit hook for LockBay development

echo "Running pre-commit checks..."

# Run black formatting
echo "Checking code formatting with black..."
if ! black --check --diff . ; then
    echo "❌ Code formatting issues found. Run 'black .' to fix."
    exit 1
fi

# Run flake8 linting
echo "Running flake8 linting..."
if ! flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics ; then
    echo "❌ Linting errors found. Please fix before committing."
    exit 1
fi

# Run tests
echo "Running tests..."
if ! python -m pytest tests/ -x ; then
    echo "❌ Tests failed. Please fix before committing."
    exit 1
fi

echo "✅ All pre-commit checks passed!"
"""

        with open(pre_commit_hook, "w") as f:
            f.write(hook_script)

        # Make executable
        os.chmod(pre_commit_hook, 0o755)

        logger.info("✅ Git hooks setup complete")

    def generate_dev_certificates(self):
        """Generate development SSL certificates"""
        ssl_dir = self.project_root / "ssl/dev"
        cert_file = ssl_dir / "cert.pem"
        key_file = ssl_dir / "key.pem"

        if cert_file.exists() and key_file.exists():
            logger.info("Development certificates already exist")
            return

        try:
            # Generate self-signed certificate for development
            subprocess.run(
                [
                    "openssl",
                    "req",
                    "-x509",
                    "-newkey",
                    "rsa:4096",
                    "-keyout",
                    str(key_file),
                    "-out",
                    str(cert_file),
                    "-days",
                    "365",
                    "-nodes",
                    "-subj",
                    "/C=US/ST=Dev/L=Dev/O=LockBay/CN=localhost",
                ],
                check=True,
                capture_output=True,
            )

            logger.info("✅ Development certificates generated")

        except subprocess.CalledProcessError as e:
            logger.warning(f"Failed to generate certificates: {e}")
        except FileNotFoundError:
            logger.warning("OpenSSL not found, skipping certificate generation")

    def create_test_data(self):
        """Create test data for development"""
        test_data_file = self.project_root / "test_data/sample_data.json"

        sample_data = {
            "users": [
                {
                    "id": 1,
                    "telegram_id": "123456789",
                    "username": "test_user_1",
                    "email": "test1@example.com",
                    "email_verified": True,
                    "phone_verified": True,
                    "reputation_score": 4.5,
                },
                {
                    "id": 2,
                    "telegram_id": "987654321",
                    "username": "test_user_2",
                    "email": "test2@example.com",
                    "email_verified": True,
                    "phone_verified": False,
                    "reputation_score": 3.8,
                },
            ],
            "escrows": [
                {
                    "id": "escrow_001",
                    "seller_id": 1,
                    "buyer_id": 2,
                    "amount": 100.00,
                    "currency": "USD",
                    "status": "active",
                    "title": "Test Escrow Transaction",
                    "description": "Sample escrow for development testing",
                }
            ],
            "transactions": [
                {
                    "id": "tx_001",
                    "user_id": 1,
                    "type": "deposit",
                    "amount": 50.00,
                    "currency": "USD",
                    "status": "completed",
                }
            ],
        }

        with open(test_data_file, "w") as f:
            json.dump(sample_data, f, indent=2)

        logger.info("✅ Test data created")

    def setup_ide_config(self):
        """Setup IDE configuration files"""
        # VS Code settings
        vscode_settings = {
            "python.defaultInterpreterPath": "./venv/bin/python",
            "python.linting.enabled": True,
            "python.linting.flake8Enabled": True,
            "python.linting.mypyEnabled": True,
            "python.formatting.provider": "black",
            "editor.formatOnSave": True,
            "files.exclude": {
                "**/__pycache__": True,
                "**/*.pyc": True,
                "**/.pytest_cache": True,
                "**/node_modules": True,
            },
            "python.testing.pytestEnabled": True,
            "python.testing.pytestArgs": ["tests/"],
        }

        vscode_dir = self.project_root / ".vscode"
        with open(vscode_dir / "settings.json", "w") as f:
            json.dump(vscode_settings, f, indent=2)

        # VS Code launch configuration
        launch_config = {
            "version": "0.2.0",
            "configurations": [
                {
                    "name": "Python: Start Bot",
                    "type": "python",
                    "request": "launch",
                    "program": "start_webhook.py",
                    "console": "integratedTerminal",
                    "envFile": "${workspaceFolder}/.env.development",
                },
                {
                    "name": "Python: Run Tests",
                    "type": "python",
                    "request": "launch",
                    "module": "pytest",
                    "args": ["tests/", "-v"],
                    "console": "integratedTerminal",
                },
            ],
        }

        with open(vscode_dir / "launch.json", "w") as f:
            json.dump(launch_config, f, indent=2)

        logger.info("✅ IDE configuration setup complete")


class ProcessManager:
    """Development process management"""

    def __init__(self):
        self.processes = {}

    def start_service(
        self,
        name: str,
        command: List[str],
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> bool:
        """Start a development service"""
        try:
            if name in self.processes:
                logger.warning(f"Service {name} already running")
                return True

            logger.info(f"Starting service: {name}")

            process = subprocess.Popen(
                command,
                cwd=cwd,
                env={**os.environ, **(env or {})},
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            self.processes[name] = {
                "process": process,
                "command": command,
                "started_at": datetime.now(),
                "status": "running",
            }

            logger.info(f"✅ Service {name} started (PID: {process.pid})")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to start service {name}: {e}")
            return False

    def stop_service(self, name: str) -> bool:
        """Stop a development service"""
        if name not in self.processes:
            logger.warning(f"Service {name} not found")
            return False

        try:
            process_info = self.processes[name]
            process = process_info["process"]

            if process.poll() is None:  # Still running
                process.terminate()

                # Wait for graceful shutdown
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()

            process_info["status"] = "stopped"
            logger.info(f"✅ Service {name} stopped")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to stop service {name}: {e}")
            return False

    def restart_service(self, name: str) -> bool:
        """Restart a development service"""
        if name in self.processes:
            self.stop_service(name)

        # Get original command
        if name in self.processes:
            command = self.processes[name]["command"]
            del self.processes[name]  # Remove old entry
            return self.start_service(name, command)

        return False

    def get_service_status(self, name: str) -> Dict[str, Any]:
        """Get service status"""
        if name not in self.processes:
            return {"status": "not_found"}

        process_info = self.processes[name]
        process = process_info["process"]

        if process.poll() is None:
            # Get process stats
            try:
                ps_process = psutil.Process(process.pid)
                cpu_percent = ps_process.cpu_percent()
                memory_info = ps_process.memory_info()

                return {
                    "status": "running",
                    "pid": process.pid,
                    "started_at": process_info["started_at"].isoformat(),
                    "cpu_percent": cpu_percent,
                    "memory_mb": memory_info.rss / 1024 / 1024,
                    "command": " ".join(process_info["command"]),
                }
            except psutil.NoSuchProcess:
                process_info["status"] = "stopped"
                return {"status": "stopped"}
        else:
            process_info["status"] = "stopped"
            return {
                "status": "stopped",
                "exit_code": process.returncode,
                "started_at": process_info["started_at"].isoformat(),
            }

    def list_services(self) -> Dict[str, Dict[str, Any]]:
        """List all services"""
        return {name: self.get_service_status(name) for name in self.processes.keys()}

    def stop_all_services(self):
        """Stop all services"""
        for name in list(self.processes.keys()):
            self.stop_service(name)


class DebugTools:
    """Development debugging utilities"""

    @staticmethod
    def setup_logging():
        """Setup development logging"""
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(logging.Formatter(log_format))

        # File handler
        file_handler = logging.FileHandler("logs/development.log")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(log_format))

        # Setup root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler)

        logger.info("✅ Development logging setup complete")

    @staticmethod
    def create_debug_endpoints():
        """Create debug endpoints for development"""
        debug_routes = """
from fastapi import APIRouter

debug_router = APIRouter(prefix="/debug")

@debug_router.get("/ping")
async def debug_ping():
    return {"message": "pong", "timestamp": time.time()}

@debug_router.get("/memory")
async def debug_memory():
    import psutil
    memory = psutil.virtual_memory()
    return {
        "total": memory.total,
        "available": memory.available,
        "percent": memory.percent,
        "used": memory.used
    }

@debug_router.get("/processes")
async def debug_processes():
    return process_manager.list_services()
"""

        debug_file = Path("debug_routes.py")
        with open(debug_file, "w") as f:
            f.write(debug_routes)

        logger.info("✅ Debug endpoints created")


# Global instances
dev_environment = None
process_manager = ProcessManager()


def initialize_development_tools(project_root: str = "."):
    """Initialize development tools"""
    global dev_environment
    dev_environment = DevelopmentEnvironment(project_root)

    # Setup logging
    DebugTools.setup_logging()

    return dev_environment


def start_development_stack():
    """Start complete development stack"""
    if not dev_environment:
        logger.error("Development environment not initialized")
        return False

    logger.info("🚀 Starting development stack...")

    # Start PostgreSQL (if using local)
    # process_manager.start_service("postgres", ["pg_ctl", "start", "-D", "/usr/local/var/postgres"])

    # Start Redis (if using local)
    # process_manager.start_service("redis", ["redis-server"])

    # Start the bot
    bot_env = {
        **dev_environment.config["environment_variables"],
        "PYTHONPATH": str(dev_environment.project_root),
    }

    process_manager.start_service(
        "bot",
        ["python", "start_webhook.py"],
        cwd=str(dev_environment.project_root),
        env=bot_env,
    )

    logger.info("✅ Development stack started")
    return True


def stop_development_stack():
    """Stop development stack"""
    logger.info("Stopping development stack...")
    process_manager.stop_all_services()
    logger.info("✅ Development stack stopped")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python development_setup.py [setup|start|stop|status]")
        sys.exit(1)

    command = sys.argv[1]

    initialize_development_tools()

    if command == "setup":
        dev_environment.setup_environment()
    elif command == "start":
        start_development_stack()
    elif command == "stop":
        stop_development_stack()
    elif command == "status":
        services = process_manager.list_services()
        print(json.dumps(services, indent=2))
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

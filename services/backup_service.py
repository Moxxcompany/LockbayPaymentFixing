"""
Automated Backup Service for Telegram Escrow Bot
Handles database backups, file backups, and configuration backups
"""

import os
import logging
import subprocess
import datetime
import json
import shutil
import tarfile
from pathlib import Path
from typing import Dict, Any, Optional
from sqlalchemy import text
from database import SessionLocal
from config import Config

logger = logging.getLogger(__name__)


class BackupService:
    """Automated backup service for database and application files"""

    def __init__(self):
        self.backup_dir = Path("backups")
        self.backup_dir.mkdir(exist_ok=True)

        # Backup retention settings
        self.daily_retention = int(os.getenv("BACKUP_DAILY_RETENTION", "7"))  # 7 days
        self.weekly_retention = int(
            os.getenv("BACKUP_WEEKLY_RETENTION", "4")
        )  # 4 weeks
        self.monthly_retention = int(
            os.getenv("BACKUP_MONTHLY_RETENTION", "6")
        )  # 6 months

        # Backup directories
        self.db_backup_dir = self.backup_dir / "database"
        self.files_backup_dir = self.backup_dir / "files"
        self.config_backup_dir = self.backup_dir / "config"

        for dir_path in [
            self.db_backup_dir,
            self.files_backup_dir,
            self.config_backup_dir,
        ]:
            dir_path.mkdir(exist_ok=True)

    async def create_full_backup(self) -> Dict[str, str]:
        """Create a complete system backup"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_results = {}

        try:
            # 1. Database backup
            db_backup_path = await self.backup_database(timestamp)
            backup_results["database"] = db_backup_path

            # 2. Application files backup
            files_backup_path = await self.backup_application_files(timestamp)
            backup_results["files"] = files_backup_path

            # 3. Configuration backup
            config_backup_path = await self.backup_configuration(timestamp)
            backup_results["config"] = config_backup_path

            # 4. Create combined backup archive
            combined_backup_path = await self.create_combined_backup(
                timestamp, backup_results
            )
            backup_results["combined"] = combined_backup_path

            logger.info(f"Full backup completed successfully: {combined_backup_path}")
            return backup_results

        except Exception as e:
            logger.error(f"Full backup failed: {e}")
            raise

    async def backup_database(self, timestamp: str) -> str:
        """Create database backup using pg_dump"""
        backup_filename = f"database_backup_{timestamp}.sql"
        backup_path = self.db_backup_dir / backup_filename

        try:
            # Parse DATABASE_URL to get connection details
            db_url = Config.DATABASE_URL
            if db_url and db_url.startswith("postgresql://"):
                # Extract connection details
                import urllib.parse

                parsed = urllib.parse.urlparse(db_url)

                host = parsed.hostname or "localhost"
                port = parsed.port or 5432
                username = parsed.username
                password = parsed.password
                database = parsed.path[1:]  # Remove leading slash

                # Set environment variables for pg_dump
                env = os.environ.copy()
                if password:
                    env["PGPASSWORD"] = password if isinstance(password, str) else password.decode('utf-8')

                # Security: Using list arguments (not shell=True) - already safe from injection
                cmd = [
                    "pg_dump",
                    "-h",
                    host,
                    "-p",
                    str(port),
                    "-U",
                    username,
                    "-d",
                    database,
                    "--no-password",
                    "--verbose",
                    "--clean",
                    "--if-exists",
                    "--create",
                ]

                # Execute pg_dump
                with open(backup_path, "w") as f:
                    result = subprocess.run(
                        cmd, stdout=f, stderr=subprocess.PIPE, env=env, text=True
                    )

                if result.returncode == 0:
                    logger.info(f"Database backup created: {backup_path}")
                    return str(backup_path)
                else:
                    raise Exception(f"pg_dump failed: {result.stderr}")
            else:
                # Fallback: Manual backup using Python
                return await self.backup_database_manual(timestamp)

        except Exception as e:
            logger.error(f"Database backup failed: {e}")
            # Try manual backup as fallback
            return await self.backup_database_manual(timestamp)

    async def backup_database_manual(self, timestamp: str) -> str:
        """Manual database backup using Python queries"""
        backup_filename = f"database_manual_{timestamp}.json"
        backup_path = self.db_backup_dir / backup_filename

        session = SessionLocal()
        backup_data = {}

        try:
            # Get all table names
            tables_query = text(
                """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
            """
            )

            tables = session.execute(tables_query).fetchall()

            for table in tables:
                table_name = table[0]
                try:
                    # Get table data
                    data_query = text(f"SELECT * FROM {table_name}")
                    rows = session.execute(data_query).fetchall()

                    # Convert to JSON-serializable format
                    backup_data[table_name] = []
                    for row in rows:
                        row_dict = {}
                        for i, column in enumerate(row._fields):
                            value = row[i]
                            # Handle datetime objects
                            if hasattr(value, "isoformat"):
                                value = value.isoformat()
                            row_dict[column] = value
                        backup_data[table_name].append(row_dict)

                    logger.info(f"Backed up table {table_name}: {len(rows)} rows")

                except Exception as e:
                    logger.warning(f"Failed to backup table {table_name}: {e}")
                    continue

            # Save backup data
            with open(backup_path, "w") as f:
                json.dump(backup_data, f, indent=2, default=str)

            logger.info(f"Manual database backup created: {backup_path}")
            return str(backup_path)

        except Exception as e:
            logger.error(f"Manual database backup failed: {e}")
            raise
        finally:
            session.close()

    async def backup_application_files(self, timestamp: str) -> str:
        """Backup important application files"""
        backup_filename = f"app_files_{timestamp}.tar.gz"
        backup_path = self.files_backup_dir / backup_filename

        # Files and directories to backup
        files_to_backup = [
            "handlers/",
            "services/",
            "utils/",
            "middleware/",
            "monitoring/",
            "caching/",
            "models.py",
            "config.py",
            "config_admin.py",
            "database.py",
            "main.py",
            "pyproject.toml",
            "replit.md",
        ]

        try:
            with tarfile.open(backup_path, "w:gz") as tar:
                for item in files_to_backup:
                    if os.path.exists(item):
                        tar.add(item, arcname=item)
                        logger.debug(f"Added {item} to backup")

            logger.info(f"Application files backup created: {backup_path}")
            return str(backup_path)

        except Exception as e:
            logger.error(f"Application files backup failed: {e}")
            raise

    async def backup_configuration(self, timestamp: str) -> str:
        """Backup configuration and environment files"""
        backup_filename = f"config_{timestamp}.json"
        backup_path = self.config_backup_dir / backup_filename

        config_data = {
            "timestamp": timestamp,
            "environment_variables": {},
            "configuration_files": {},
        }

        try:
            # Backup important environment variables (without secrets)
            safe_env_vars = [
                "BACKUP_DAILY_RETENTION",
                "BACKUP_WEEKLY_RETENTION",
                "BACKUP_MONTHLY_RETENTION",
                "PLATFORM_FEE_PERCENTAGE",
                "MINIMUM_ESCROW_AMOUNT",
                "ADMIN_IDS",
            ]

            for var in safe_env_vars:
                if var in os.environ:
                    config_data["environment_variables"][var] = os.environ[var]

            # Backup configuration files
            config_files = [".env.example"]
            for config_file in config_files:
                if os.path.exists(config_file):
                    with open(config_file, "r") as f:
                        config_data["configuration_files"][config_file] = f.read()

            # Save configuration backup
            with open(backup_path, "w") as f:
                json.dump(config_data, f, indent=2)

            logger.info(f"Configuration backup created: {backup_path}")
            return str(backup_path)

        except Exception as e:
            logger.error(f"Configuration backup failed: {e}")
            raise

    async def create_combined_backup(
        self, timestamp: str, backup_results: Dict[str, str]
    ) -> str:
        """Create a combined backup archive"""
        combined_filename = f"full_backup_{timestamp}.tar.gz"
        combined_path = self.backup_dir / combined_filename

        try:
            with tarfile.open(combined_path, "w:gz") as tar:
                for backup_type, backup_path in backup_results.items():
                    if backup_type != "combined" and os.path.exists(backup_path):
                        tar.add(
                            backup_path,
                            arcname=f"{backup_type}/{os.path.basename(backup_path)}",
                        )

            logger.info(f"Combined backup created: {combined_path}")
            return str(combined_path)

        except Exception as e:
            logger.error(f"Combined backup creation failed: {e}")
            raise

    async def cleanup_old_backups(self):
        """Remove old backups based on retention policy"""
        try:
            now = datetime.datetime.now()

            # Daily backups cleanup
            cutoff_date = now - datetime.timedelta(days=self.daily_retention)
            await self._cleanup_backups_by_date(self.backup_dir, cutoff_date, "daily")

            logger.info("Old backups cleaned up successfully")

        except Exception as e:
            logger.error(f"Backup cleanup failed: {e}")

    async def _cleanup_backups_by_date(
        self, directory: Path, cutoff_date: datetime.datetime, backup_type: str
    ):
        """Helper method to cleanup backups older than cutoff date"""
        deleted_count = 0

        for backup_file in directory.glob("*.tar.gz"):
            try:
                # Extract timestamp from filename
                filename = backup_file.name
                if "full_backup_" in filename:
                    timestamp_str = filename.replace("full_backup_", "").replace(
                        ".tar.gz", ""
                    )
                    backup_date = datetime.datetime.strptime(
                        timestamp_str, "%Y%m%d_%H%M%S"
                    )

                    if backup_date < cutoff_date:
                        backup_file.unlink()
                        deleted_count += 1
                        logger.debug(f"Deleted old {backup_type} backup: {backup_file}")

            except Exception as e:
                logger.warning(f"Failed to process backup file {backup_file}: {e}")
                continue

        if deleted_count > 0:
            logger.info(f"Deleted {deleted_count} old {backup_type} backups")

    async def restore_from_backup(
        self, backup_path: str, restore_type: str = "full"
    ) -> bool:
        """Restore system from backup (use with extreme caution)"""
        try:
            logger.warning(f"Starting restore from backup: {backup_path}")

            if not os.path.exists(backup_path):
                raise FileNotFoundError(f"Backup file not found: {backup_path}")

            # Create restore directory
            restore_dir = Path("restore_temp")
            restore_dir.mkdir(exist_ok=True)

            try:
                # Extract backup archive
                if backup_path.endswith(".tar.gz"):
                    await self._extract_backup_archive(backup_path, restore_dir)
                else:
                    # Single file backup (database only)
                    await self._restore_database_only(backup_path)
                    return True

                # Restore based on type
                if restore_type == "full":
                    success = await self._restore_full_system(restore_dir)
                elif restore_type == "database_only":
                    success = await self._restore_database_from_archive(restore_dir)
                elif restore_type == "files_only":
                    success = await self._restore_files_from_archive(restore_dir)
                elif restore_type == "config_only":
                    success = await self._restore_config_from_archive(restore_dir)
                else:
                    raise ValueError(f"Invalid restore type: {restore_type}")

                return success

            finally:
                # Cleanup restore directory
                if restore_dir.exists():
                    shutil.rmtree(restore_dir)

        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False

    async def _extract_backup_archive(self, backup_path: str, restore_dir: Path):
        """Extract backup archive to restore directory"""
        try:
            with tarfile.open(backup_path, "r:gz") as tar:
                tar.extractall(path=restore_dir)
            logger.info(f"Successfully extracted backup archive to {restore_dir}")

        except Exception as e:
            logger.error(f"Failed to extract backup archive: {e}")
            raise

    async def _restore_full_system(self, restore_dir: Path) -> bool:
        """Restore complete system from extracted backup"""
        try:
            success_flags = []

            # 1. Restore database
            db_success = await self._restore_database_from_archive(restore_dir)
            success_flags.append(db_success)

            # 2. Restore application files
            files_success = await self._restore_files_from_archive(restore_dir)
            success_flags.append(files_success)

            # 3. Restore configuration
            config_success = await self._restore_config_from_archive(restore_dir)
            success_flags.append(config_success)

            # Check if all restorations were successful
            if all(success_flags):
                logger.info("Full system restore completed successfully")
                await self._log_restore_event("full_system", "success")
                return True
            else:
                logger.error(f"Partial restore failure. Success flags: {success_flags}")
                await self._log_restore_event(
                    "full_system", "partial_failure", {"success_flags": success_flags}
                )
                return False

        except Exception as e:
            logger.error(f"Full system restore failed: {e}")
            await self._log_restore_event("full_system", "failure", {"error": str(e)})
            return False

    async def _restore_database_from_archive(self, restore_dir: Path) -> bool:
        """Restore database from extracted backup files"""
        try:
            # Find database backup file
            db_files = list(restore_dir.glob("**/database_backup_*.sql"))
            if not db_files:
                logger.error("No database backup file found in archive")
                return False

            db_backup_file = db_files[0]  # Use the first (most recent) database backup
            return await self._restore_database_only(str(db_backup_file))

        except Exception as e:
            logger.error(f"Database restore from archive failed: {e}")
            return False

    async def _restore_database_only(self, sql_backup_path: str) -> bool:
        """Restore database from SQL backup file"""
        try:
            logger.warning(
                "Starting database restoration - this will replace all current data!"
            )

            # Get database connection parameters from Config (supports Railway failover)
            from config import Config
            db_url = Config.DATABASE_URL
            if not db_url:
                raise ValueError("Database URL not configured in Config.DATABASE_URL")

            # Parse database URL
            import urllib.parse

            parsed = urllib.parse.urlparse(db_url)

            db_params = {
                "host": parsed.hostname,
                "port": parsed.port or 5432,
                "database": parsed.path[1:],  # Remove leading slash
                "username": parsed.username,
                "password": parsed.password,
            }

            # Create backup of current database before restore
            current_backup = await self.backup_database(
                f"pre_restore_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            logger.info(f"Created safety backup: {current_backup}")

            # Drop all existing tables (dangerous!)
            await self._drop_all_tables()

            # Security: Using list arguments (not shell=True) - already safe from injection
            restore_command = [
                "psql",
                "-h",
                str(db_params["host"]),
                "-p",
                str(db_params["port"]),
                "-U",
                db_params["username"],
                "-d",
                db_params["database"],
                "-f",
                sql_backup_path,
                "-v",
                "ON_ERROR_STOP=1",
            ]

            env = os.environ.copy()
            env["PGPASSWORD"] = db_params["password"]

            result = subprocess.run(
                restore_command,
                env=env,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minutes timeout
            )

            if result.returncode == 0:
                logger.info("Database restoration completed successfully")
                await self._log_restore_event("database", "success")
                return True
            else:
                logger.error(f"Database restoration failed: {result.stderr}")
                await self._log_restore_event(
                    "database", "failure", {"error": result.stderr}
                )

                # Attempt to restore from safety backup
                logger.warning("Attempting to restore from safety backup...")
                await self._restore_database_only(current_backup)
                return False

        except Exception as e:
            logger.error(f"Database restoration failed: {e}")
            await self._log_restore_event("database", "failure", {"error": str(e)})
            return False

    async def _drop_all_tables(self):
        """Drop all tables in the database (for clean restore)"""
        try:
            session = SessionLocal()
            try:
                # Get all table names
                result = session.execute(
                    text(
                        """
                    SELECT tablename FROM pg_tables 
                    WHERE schemaname = 'public'
                """
                    )
                )

                tables = [row[0] for row in result.fetchall()]

                # Drop all tables with CASCADE (using safe parameterized identifier quoting)
                from sqlalchemy import sql
                for table in tables:
                    # Safely quote the identifier to prevent SQL injection
                    safe_table_name = sql.quoted_name(table, quote=True)
                    session.execute(text(f"DROP TABLE IF EXISTS {safe_table_name} CASCADE"))

                session.commit()
                logger.info(f"Dropped {len(tables)} tables for clean restore")

            finally:
                session.close()

        except Exception as e:
            logger.error(f"Failed to drop tables: {e}")
            raise

    async def _restore_files_from_archive(self, restore_dir: Path) -> bool:
        """Restore application files from backup"""
        try:
            # Find files backup directory
            files_backup_dirs = list(restore_dir.glob("**/files_backup_*"))
            if not files_backup_dirs:
                logger.warning("No files backup found in archive")
                return True  # Not critical for system operation

            files_backup_dir = files_backup_dirs[0]

            # Critical directories to restore
            critical_dirs = ["handlers", "services", "utils", "middleware", "jobs"]

            for dir_name in critical_dirs:
                source_dir = files_backup_dir / dir_name
                target_dir = Path(dir_name)

                if source_dir.exists():
                    # Backup existing directory
                    if target_dir.exists():
                        backup_name = f"{dir_name}_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        shutil.move(str(target_dir), backup_name)

                    # Restore from backup
                    shutil.copytree(str(source_dir), str(target_dir))
                    logger.info(f"Restored directory: {dir_name}")

            logger.info("Application files restoration completed")
            await self._log_restore_event("files", "success")
            return True

        except Exception as e:
            logger.error(f"Files restoration failed: {e}")
            await self._log_restore_event("files", "failure", {"error": str(e)})
            return False

    async def _restore_config_from_archive(self, restore_dir: Path) -> bool:
        """Restore configuration files from backup"""
        try:
            # Find config backup directory
            config_backup_dirs = list(restore_dir.glob("**/config_backup_*"))
            if not config_backup_dirs:
                logger.warning("No config backup found in archive")
                return True  # Not critical

            config_backup_dir = config_backup_dirs[0]

            # Restore configuration files
            config_files = ["config.py", ".env.example", "pyproject.toml"]

            for config_file in config_files:
                source_file = config_backup_dir / config_file
                target_file = Path(config_file)

                if source_file.exists():
                    # Backup existing file
                    if target_file.exists():
                        backup_name = f"{config_file}.backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        shutil.copy2(str(target_file), backup_name)

                    # Restore from backup
                    shutil.copy2(str(source_file), str(target_file))
                    logger.info(f"Restored config file: {config_file}")

            logger.info("Configuration restoration completed")
            await self._log_restore_event("config", "success")
            return True

        except Exception as e:
            logger.error(f"Configuration restoration failed: {e}")
            await self._log_restore_event("config", "failure", {"error": str(e)})
            return False

    async def _log_restore_event(
        self, restore_type: str, status: str, details: Optional[Dict[str, Any]] = None
    ):
        """Log restore events for audit purposes"""
        try:
            # Audit logging is optional - log locally if audit system not available
            logger.info(f"Restore event: {restore_type} - {status} - {details or {}}")
            
        except Exception as e:
            logger.warning(f"Failed to log restore event (non-critical): {e}")

    async def validate_backup_integrity(self, backup_path: str) -> Dict[str, Any]:
        """Validate backup file integrity and contents"""
        try:
            validation_results = {
                "is_valid": False,
                "file_exists": False,
                "is_readable": False,
                "archive_valid": False,
                "contains_database": False,
                "contains_files": False,
                "contains_config": False,
                "file_size": 0,
                "creation_date": None,
                "errors": [],
            }

            # Check file existence
            if not os.path.exists(backup_path):
                validation_results["errors"].append("Backup file does not exist")
                return validation_results

            validation_results["file_exists"] = True
            validation_results["file_size"] = os.path.getsize(backup_path)
            validation_results["creation_date"] = datetime.datetime.fromtimestamp(
                os.path.getctime(backup_path)
            ).isoformat()

            # Check if file is readable
            try:
                with open(backup_path, "rb") as f:
                    f.read(1024)  # Read first 1KB
                validation_results["is_readable"] = True
            except Exception as e:
                validation_results["errors"].append(f"File not readable: {str(e)}")
                return validation_results

            # Check archive validity
            if backup_path.endswith(".tar.gz"):
                try:
                    with tarfile.open(backup_path, "r:gz") as tar:
                        # List archive contents
                        members = tar.getnames()
                        validation_results["archive_valid"] = True

                        # Check for expected contents
                        validation_results["contains_database"] = any(
                            "database_backup_" in member for member in members
                        )
                        validation_results["contains_files"] = any(
                            "files_backup_" in member for member in members
                        )
                        validation_results["contains_config"] = any(
                            "config_backup_" in member for member in members
                        )

                except Exception as e:
                    validation_results["errors"].append(
                        f"Archive validation failed: {str(e)}"
                    )
                    return validation_results

            elif backup_path.endswith(".sql"):
                # Single database backup
                validation_results["archive_valid"] = True
                validation_results["contains_database"] = True

            # Overall validation
            validation_results["is_valid"] = (
                validation_results["file_exists"]
                and validation_results["is_readable"]
                and validation_results["archive_valid"]
                and len(validation_results["errors"]) == 0
            )

            return validation_results

        except Exception as e:
            logger.error(f"Backup validation failed: {e}")
            return {"is_valid": False, "errors": [f"Validation error: {str(e)}"]}

    async def get_backup_status(self) -> Dict:
        """Get backup system status and statistics"""
        try:
            backup_stats = {
                "backup_directory": str(self.backup_dir),
                "retention_policy": {
                    "daily": self.daily_retention,
                    "weekly": self.weekly_retention,
                    "monthly": self.monthly_retention,
                },
                "backup_counts": {},
                "total_backup_size": 0,
                "latest_backup": None,
            }

            # Count backup files
            for backup_type in ["database", "files", "config"]:
                backup_subdir = self.backup_dir / backup_type
                if backup_subdir.exists():
                    backup_files = list(backup_subdir.glob("*"))
                    backup_stats["backup_counts"][backup_type] = len(backup_files)

            # Combined backups
            combined_backups = list(self.backup_dir.glob("full_backup_*.tar.gz"))
            backup_stats["backup_counts"]["combined"] = len(combined_backups)

            # Find latest backup
            if combined_backups:
                latest_backup = max(combined_backups, key=os.path.getctime)
                backup_stats["latest_backup"] = {
                    "filename": latest_backup.name,
                    "created": datetime.datetime.fromtimestamp(
                        os.path.getctime(latest_backup)
                    ).isoformat(),
                    "size_mb": round(os.path.getsize(latest_backup) / (1024 * 1024), 2),
                }

            # Total backup size
            total_size = 0
            for backup_file in self.backup_dir.rglob("*"):
                if backup_file.is_file():
                    total_size += os.path.getsize(backup_file)
            backup_stats["total_backup_size"] = round(
                total_size / (1024 * 1024), 2
            )  # MB

            return backup_stats

        except Exception as e:
            logger.error(f"Failed to get backup status: {e}")
            return {"error": str(e)}


# Global backup service instance
backup_service = BackupService()


# Backup functions for scheduler
async def daily_backup():
    """Daily backup job for scheduler"""
    try:
        logger.info("Starting daily automated backup")
        await backup_service.create_full_backup()
        await backup_service.cleanup_old_backups()
        logger.info("Daily backup completed successfully")
    except Exception as e:
        logger.error(f"Daily backup failed: {e}")


async def weekly_backup():
    """Weekly backup job for scheduler"""
    try:
        logger.info("Starting weekly automated backup")
        backup_results = await backup_service.create_full_backup()

        # Mark as weekly backup by copying to weekly directory
        weekly_dir = backup_service.backup_dir / "weekly"
        weekly_dir.mkdir(exist_ok=True)

        if "combined" in backup_results:
            source_path = Path(backup_results["combined"])
            weekly_path = weekly_dir / f"weekly_{source_path.name}"
            shutil.copy2(source_path, weekly_path)
            logger.info(f"Weekly backup saved: {weekly_path}")

        logger.info("Weekly backup completed successfully")
    except Exception as e:
        logger.error(f"Weekly backup failed: {e}")

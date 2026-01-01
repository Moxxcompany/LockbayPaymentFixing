"""Comprehensive file analysis and validation service"""

import logging
import magic
import filetype
from typing import Dict, List
import hashlib
import os

logger = logging.getLogger(__name__)


class FileAnalysisService:
    """Comprehensive file analysis and validation"""

    # Security-focused file type definitions
    SAFE_MIME_TYPES = {
        # Images
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/gif",
        "image/webp",
        "image/bmp",
        # Documents
        "application/pdf",
        "text/plain",
        "text/csv",
        # Audio
        "audio/mpeg",
        "audio/mp3",
        "audio/wav",
        "audio/ogg",
        # Video
        "video/mp4",
        "video/mpeg",
        "video/quicktime",
        "video/webm",
        # Archives (with restrictions)
        "application/zip",
        "application/x-zip-compressed",
    }

    DANGEROUS_EXTENSIONS = {
        ".exe",
        ".bat",
        ".cmd",
        ".com",
        ".pif",
        ".scr",
        ".vbs",
        ".js",
        ".jar",
        ".sh",
        ".ps1",
        ".msi",
        ".app",
        ".deb",
        ".rpm",
        ".dmg",
        ".pkg",
    }

    MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB

    @classmethod
    def analyze_file(cls, file_content: bytes, filename: str) -> Dict:
        """Comprehensive file analysis"""
        try:
            analysis_result = {
                "filename": filename,
                "size": len(file_content),
                "is_safe": False,
                "mime_type": None,
                "detected_type": None,
                "file_hash": None,
                "validation_errors": [],
                "warnings": [],
                "file_category": None,
                "metadata": {},
            }

            # Basic size validation
            if len(file_content) > cls.MAX_FILE_SIZE:
                analysis_result["validation_errors"].append(
                    f"File too large: {len(file_content)} bytes (max: {cls.MAX_FILE_SIZE})"
                )
                return analysis_result

            if len(file_content) == 0:
                analysis_result["validation_errors"].append("Empty file")
                return analysis_result

            # Generate file hash for integrity
            analysis_result["file_hash"] = hashlib.sha256(file_content).hexdigest()

            # Detect MIME type using python-magic
            try:
                mime_type = magic.from_buffer(file_content, mime=True)
                analysis_result["mime_type"] = mime_type
            except (ImportError, AttributeError, OSError) as e:
                logger.warning(f"Magic MIME detection failed: {e}")
                analysis_result["warnings"].append("Could not detect MIME type")
            except Exception as e:
                logger.warning(f"Unexpected MIME detection error: {e}")
                analysis_result["warnings"].append("MIME detection error")

            # Detect file type using filetype library
            try:
                detected = filetype.guess(file_content)
                if detected:
                    analysis_result["detected_type"] = detected.extension
                    analysis_result["metadata"]["detected_mime"] = detected.mime
            except (ImportError, AttributeError) as e:
                logger.warning(f"Filetype detection failed: {e}")
            except Exception as e:
                logger.warning(f"Unexpected filetype detection error: {e}")

            # Validate file extension
            file_ext = os.path.splitext(filename.lower())[1]
            if file_ext in cls.DANGEROUS_EXTENSIONS:
                analysis_result["validation_errors"].append(
                    f"Dangerous file extension: {file_ext}"
                )
                return analysis_result

            # Categorize file
            analysis_result["file_category"] = cls._categorize_file(
                analysis_result["mime_type"], file_ext
            )

            # Security validation
            security_check = cls._security_validation(file_content, analysis_result)
            analysis_result.update(security_check)

            # Final safety determination
            analysis_result["is_safe"] = (
                len(analysis_result["validation_errors"]) == 0
                and analysis_result["mime_type"] in cls.SAFE_MIME_TYPES
            )

            return analysis_result

        except Exception as e:
            logger.error(f"File analysis failed: {e}", exc_info=True)
            return {
                "filename": filename,
                "is_safe": False,
                "validation_errors": [f"Analysis failed: {str(e)}"],
                "size": len(file_content) if file_content else 0,
            }

    @classmethod
    def _categorize_file(cls, mime_type: str, extension: str) -> str:
        """Categorize file based on MIME type and extension"""
        if not mime_type:
            return "unknown"

        if mime_type.startswith("image/"):
            return "image"
        elif mime_type.startswith("video/"):
            return "video"
        elif mime_type.startswith("audio/"):
            return "audio"
        elif mime_type in ["application/pdf"]:
            return "document"
        elif mime_type.startswith("text/"):
            return "text"
        elif mime_type in ["application/zip", "application/x-zip-compressed"]:
            return "archive"
        else:
            return "other"

    @classmethod
    def _security_validation(cls, file_content: bytes, analysis: Dict) -> Dict:
        """Perform security-focused validation"""
        security_result = {
            "security_warnings": [],
            "security_score": 100,  # Start with perfect score
        }

        # Check for embedded executables in images/documents
        if analysis["file_category"] in ["image", "document"]:
            if cls._check_for_embedded_content(file_content):
                security_result["security_warnings"].append(
                    "Possible embedded content detected"
                )
                security_result["security_score"] -= 30

        # Check file header consistency
        if not cls._validate_file_header(file_content, analysis["mime_type"]):
            security_result["security_warnings"].append("File header mismatch")
            security_result["security_score"] -= 20

        # Check for suspicious patterns
        suspicious_patterns = cls._check_suspicious_patterns(file_content)
        if suspicious_patterns:
            security_result["security_warnings"].extend(suspicious_patterns)
            security_result["security_score"] -= len(suspicious_patterns) * 15

        return security_result

    @classmethod
    def _check_for_embedded_content(cls, file_content: bytes) -> bool:
        """Check for potentially embedded executable content"""
        # Common executable signatures
        exe_signatures = [
            b"MZ",  # Windows PE
            b"\x7fELF",  # Linux ELF
            b"\xfe\xed\xfa",  # Mach-O
            b"PK\x03\x04",  # ZIP (could contain executables)
        ]

        for signature in exe_signatures:
            if signature in file_content[100:]:  # Skip normal headers
                return True
        return False

    @classmethod
    def _validate_file_header(cls, file_content: bytes, mime_type: str) -> bool:
        """Validate file header matches declared MIME type"""
        if not mime_type or len(file_content) < 8:
            return True  # Can't validate

        header_validators = {
            "image/jpeg": [b"\xff\xd8\xff"],
            "image/png": [b"\x89PNG\r\n\x1a\n"],
            "image/gif": [b"GIF87a", b"GIF89a"],
            "application/pdf": [b"%PDF-"],
            "video/mp4": [b"ftyp"],
            "application/zip": [b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"],
        }

        expected_headers = header_validators.get(mime_type, [])
        if not expected_headers:
            return True  # No validation rule

        for header in expected_headers:
            if file_content.startswith(header) or header in file_content[:20]:
                return True

        return False

    @classmethod
    def _check_suspicious_patterns(cls, file_content: bytes) -> List[str]:
        """Check for suspicious patterns in file content"""
        warnings = []

        # Check for script injections
        script_patterns = [
            b"<script",
            b"javascript:",
            b"vbscript:",
            b"data:text/html",
            b"eval(",
            b"exec(",
            b"system(",
            b"shell_exec",
        ]

        for pattern in script_patterns:
            if pattern in file_content.lower():
                warnings.append(
                    f"Suspicious pattern detected: {pattern.decode('utf-8', errors='ignore')}"
                )

        # Check for excessive null bytes (common in malware)
        null_ratio = file_content.count(b"\x00") / len(file_content)
        if null_ratio > 0.3:
            warnings.append("Excessive null bytes detected")

        return warnings

    @classmethod
    def get_safe_filename(cls, filename: str) -> str:
        """Generate a safe filename for storage"""
        # Remove dangerous characters
        safe_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-_"
        safe_filename = "".join(c for c in filename if c in safe_chars)

        # Ensure it's not empty and has reasonable length
        if not safe_filename or len(safe_filename) < 3:
            safe_filename = "file"

        if len(safe_filename) > 100:
            name, ext = os.path.splitext(safe_filename)
            safe_filename = name[:95] + ext

        return safe_filename

    @classmethod
    def format_analysis_report(cls, analysis: Dict) -> str:
        """Format analysis results for user display"""
        if not analysis["is_safe"]:
            return "❌ File Rejected\n\n" + "\n".join(
                [f"• {error}" for error in analysis["validation_errors"]]
            )

        report = "✅ File Analysis Complete\n\n"
        report += f"📄 File: {analysis['filename']}\n"
        report += f"📊 Size: {analysis['size']:,} bytes\n"
        report += f"🔍 Type: {analysis['file_category'].title()}\n"

        if analysis.get("security_score", 100) < 100:
            report += f"🛡️ Security Score: {analysis['security_score']}/100\n"

        if analysis.get("warnings"):
            report += f"⚠️ Warnings: {len(analysis['warnings'])}\n"

        return report

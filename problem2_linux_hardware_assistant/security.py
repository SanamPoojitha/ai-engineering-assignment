"""
Security and Privilege Management Layer for Linux System Inspection.
Enforces read-only execution, zero arbitrary shell execution, argument pinning,
environment sanitation, and privilege separation (root / non-root handling).
"""

import os
import re
import shutil
from typing import List, Optional, Tuple
from .config import (
    ALLOWED_COMMAND_SCHEMAS,
    ALLOWED_SYSFS_PATHS,
    COMMAND_TIMEOUT_SECONDS,
    SAFE_LOCALE,
    SAFE_PATH,
)


class SecurityViolationError(Exception):
    """Raised when an unsafe or non-allowlisted command execution is attempted."""
    pass


class CommandSecurityValidator:
    """
    Guarantees that only strictly allowlisted, read-only system inspection commands
    can be executed by the tool layer.
    """

    DANGEROUS_CHARS = re.compile(r"[;&|`$><!(){}\n\r\x00]")

    @classmethod
    def validate_command(cls, binary: str, args: List[str]) -> Tuple[str, List[str]]:
        """
        Validates binary and arguments against the immutable allowlist.
        Returns the sanitized (absolute_binary_path, validated_args_tuple).
        Raises SecurityViolationError on any deviation.
        """
        # 1. Base binary check
        base_binary = os.path.basename(binary).strip()
        if base_binary not in ALLOWED_COMMAND_SCHEMAS:
            raise SecurityViolationError(
                f"Binary '{base_binary}' is NOT in the allowlist of safe inspection tools. "
                f"Allowed: {list(ALLOWED_COMMAND_SCHEMAS.keys())}"
            )

        # 2. Prevent shell metacharacters in binary name or any argument
        for arg in args:
            if cls.DANGEROUS_CHARS.search(arg):
                raise SecurityViolationError(
                    f"Command arguments contain prohibited shell metacharacters: '{arg}'"
                )

        # 3. Match against allowed argument schemas for this binary
        args_tuple = tuple(args)
        allowed_schemas = ALLOWED_COMMAND_SCHEMAS[base_binary]

        if args_tuple not in allowed_schemas:
            raise SecurityViolationError(
                f"Arguments {args} for binary '{base_binary}' are not permitted. "
                f"Allowed schemas: {allowed_schemas}"
            )

        # 4. Resolve binary path safely using restricted PATH
        resolved_path = shutil.which(base_binary, path=SAFE_PATH)
        if not resolved_path:
            # Check standard fallback locations
            for candidate in ["/usr/sbin", "/sbin", "/usr/bin", "/bin"]:
                full = os.path.join(candidate, base_binary)
                if os.path.exists(full) and os.access(full, os.X_OK):
                    resolved_path = full
                    break

        return resolved_path or base_binary, list(args_tuple)

    @classmethod
    def get_sanitized_environment(cls) -> dict:
        """Returns a minimal, clean environment dict to prevent environment poisoning."""
        return {
            "PATH": SAFE_PATH,
            "LANG": SAFE_LOCALE,
            "LC_ALL": SAFE_LOCALE,
            "TERM": "dumb",
        }

    @classmethod
    def validate_sysfs_read(cls, file_path: str) -> str:
        """Validates that a virtual filesystem read is within allowlisted /proc or /sys paths."""
        real_path = os.path.abspath(file_path)
        is_allowed = any(real_path.startswith(os.path.abspath(allowed)) for allowed in ALLOWED_SYSFS_PATHS)
        if not is_allowed:
            raise SecurityViolationError(f"Access to path '{real_path}' is not allowlisted.")
        return real_path


class PrivilegeManager:
    """
    Manages execution permissions for commands requiring elevated privileges (e.g., dmidecode).
    Implements least-privilege checks and non-interactive sudo verification.
    """

    @staticmethod
    def is_root() -> bool:
        """Checks if current process is running as root."""
        if hasattr(os, "geteuid"):
            return os.geteuid() == 0
        return False

    @staticmethod
    def can_run_sudo_non_interactive(binary: str) -> bool:
        """
        Tests whether sudo can execute the binary non-interactively (via sudoers NOPASSWD rule)
        without prompting for a password.
        """
        if not hasattr(os, "geteuid"):
            return False

        sudo_bin = shutil.which("sudo", path=SAFE_PATH)
        if not sudo_bin:
            return False

        import subprocess
        try:
            res = subprocess.run(
                [sudo_bin, "-n", "-l", binary],
                capture_output=True,
                text=True,
                timeout=2.0
            )
            return res.returncode == 0
        except Exception:
            return False

"""Curl tool for executing HTTP requests."""

from __future__ import annotations

import shlex
import subprocess


def execute_curl(command: str, timeout: int = 30) -> dict:
    """Execute a curl command on the server.

    Args:
        command: Full curl command string (e.g., "curl -s http://localhost:7700/health")
        timeout: Command timeout in seconds (default 30)

    Returns:
        Dict with 'success', 'output', and optionally 'error' keys.
    """
    # Parse the command string into arguments
    try:
        args = shlex.split(command)
    except ValueError as e:
        return {"success": False, "output": "", "error": f"Failed to parse command: {e}"}

    # Ensure the command starts with curl
    if not args or args[0] != "curl":
        return {"success": False, "output": "", "error": "Command must start with 'curl'"}

    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        if result.returncode == 0:
            return {"success": True, "output": result.stdout}
        else:
            return {
                "success": False,
                "output": result.stdout,
                "error": result.stderr or f"Exit code: {result.returncode}",
            }

    except subprocess.TimeoutExpired:
        return {"success": False, "output": "", "error": f"Command timed out after {timeout}s"}
    except FileNotFoundError:
        return {"success": False, "output": "", "error": "curl not found on system"}
    except Exception as e:
        return {"success": False, "output": "", "error": str(e)}

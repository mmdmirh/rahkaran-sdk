"""
Compatibility patch for the external `rahkaran_auth` library.

`rahkaran_auth` shells out to Node.js to perform the RSA password encryption
of the Rahkaran login handshake. On constrained hosts (e.g. Azure App Service)
the `node` binary is not on PATH for subprocesses, so the login fails.

This module patches `RahkaranAuth._encrypt_password` to:
  1. Resolve the node binary from the active virtualenv and common locations.
  2. Fall back to installing Node via `nodeenv` into the virtualenv at runtime.
"""
import logging
import os
import shutil
import subprocess
import sys

logger = logging.getLogger(__name__)

_PATCH_APPLIED = False

_NODE_CANDIDATES = [
    os.path.join(sys.exec_prefix, "bin", "node"),  # virtualenv
    "/home/site/wwwroot/node/bin/node",            # Azure App Service
    "/usr/bin/node",
    "/usr/local/bin/node",
    "/opt/node/bin/node",
]


def _resolve_node_binary() -> str:
    for path in _NODE_CANDIDATES:
        if os.path.exists(path):
            return path

    found = shutil.which("node")
    if found:
        return found

    # Last resort: install Node into the current virtualenv via nodeenv.
    venv_node = _NODE_CANDIDATES[0]
    logger.warning("Node.js not found. Attempting runtime installation via nodeenv...")
    try:
        subprocess.check_call(
            [sys.executable, "-m", "nodeenv", "-p", "--node=20.10.0", "--prebuilt"]
        )
        if os.path.exists(venv_node):
            logger.info(f"Node.js installed at {venv_node}")
            return venv_node
    except Exception as e:
        logger.error(f"Runtime Node.js installation failed: {e}")

    # Let subprocess raise a clear FileNotFoundError if this doesn't resolve.
    return "node"


def _patched_encrypt_password(self, password: str, rsa_e: str, rsa_m: str, session_id: str) -> str:
    script_path = self.scripts_dir / "rsa_encrypt.js"
    if not script_path.exists():
        raise FileNotFoundError(f"RSA encryption script not found: {script_path}")

    node_cmd = _resolve_node_binary()
    try:
        result = subprocess.run(
            [node_cmd, str(script_path), password, rsa_e, rsa_m, session_id],
            cwd=str(self.scripts_dir),
            capture_output=True,
            text=True,
            timeout=10,
        )
    except FileNotFoundError:
        logger.error(f"Node executable '{node_cmd}' not found. PATH: {os.environ.get('PATH')}")
        raise

    if result.returncode != 0:
        raise RuntimeError(f"RSA encryption failed: {result.stderr}")
    return result.stdout.strip()


def patch_rahkaran_auth() -> bool:
    """
    Apply the node-resolution patch to `rahkaran_auth.RahkaranAuth`.
    Safe to call multiple times. Returns True if the patch is in effect.
    """
    global _PATCH_APPLIED
    if _PATCH_APPLIED:
        return True

    try:
        from rahkaran_auth import RahkaranAuth
    except ImportError:
        return False

    RahkaranAuth._encrypt_password = _patched_encrypt_password
    _PATCH_APPLIED = True
    return True

"""Configuration and logging setup."""

import os
import logging
from pathlib import Path

# =============================================================================
# Logging
# =============================================================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp")
logger.setLevel(logging.DEBUG)

# =============================================================================
# Configuration
# =============================================================================
SERVER_PORT = 8090
INSTRUCTIONS_DIR = Path(
    os.environ.get("INSTRUCTIONS_DIR", "~/.mcp-commands")
).expanduser()
FILES_DIR = Path(os.environ.get("FILES_DIR", "~/.mcp-commands/files")).expanduser()

# Ensure directories exist
for p in [INSTRUCTIONS_DIR, FILES_DIR]:
    p.mkdir(parents=True, exist_ok=True)

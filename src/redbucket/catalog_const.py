"""与 api-catalog 对齐的枚举。未知值直接拒绝。"""
from __future__ import annotations

HARNESSES = ("codex", "agents", "claude", "openclaw")
ASSET_TYPES = ("skill", "mcp", "instructions", "subagent", "plugin")
VISIBILITIES = ("public", "private")
STORAGE_LIMIT = 10485760
DEFAULT_QUOTA = 5
INSTRUCTIONS_MAX = 1048576
DEVICE_CODE_TTL = 600
DEVICE_POLL_INTERVAL = 5

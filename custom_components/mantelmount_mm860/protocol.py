"""Protocol parsing for MantelMount MM860."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Field map confirmed from Control4 driver
# MMQ<csv...>
# 0  STATUS
# 1  MOUNT_ELEVATION
# 2  MOUNT_AZIMUTH
# 3  LEFT_ACTUATOR_POSITION
# 4  RIGHT_ACTUATOR_POSITION
# 5  LAST_PRESET
# 6  TEMPERATURE
# 7  TV_STATE
# 8  LAST_EVENT_SOURCE
# 9  FIRMWARE_VERSION
# 10 LOST_FLAG
# 11 TV_CURRENT
# 12 LEFT_AT_LIMIT
# 13 RIGHT_AT_LIMIT
# 14 LEFT_MOTOR_CURRENT
# 15 RIGHT_MOTOR_CURRENT


@dataclass(frozen=True)
class MMQStatus:
    """Parsed MMQ status response."""

    raw: str
    status: int
    elevation: int
    azimuth: int
    left_actuator: int
    right_actuator: int
    last_preset: int
    temperature: int
    tv_state: int
    last_event_source: int
    firmware_version: int
    lost_flag: int
    tv_current: int
    left_at_limit: int
    right_at_limit: int
    left_motor_current: int
    right_motor_current: int

    def as_attrs(self) -> dict[str, Any]:
        """Return all attributes as a dictionary."""
        return {
            "raw": self.raw,
            "status": self.status,
            "elevation": self.elevation,
            "azimuth": self.azimuth,
            "left_actuator": self.left_actuator,
            "right_actuator": self.right_actuator,
            "last_preset": self.last_preset,
            "temperature": self.temperature,
            "tv_state": self.tv_state,
            "last_event_source": self.last_event_source,
            "firmware_version": self.firmware_version,
            "lost_flag": self.lost_flag,
            "tv_current": self.tv_current,
            "left_at_limit": self.left_at_limit,
            "right_at_limit": self.right_at_limit,
            "left_motor_current": self.left_motor_current,
            "right_motor_current": self.right_motor_current,
        }


def _clean_raw(raw: str) -> str:
    """Clean the raw MMQ response."""
    s = (raw or "").strip()
    # If device echoes "MMQ" then response also includes MMQ..., keep last MMQ segment.
    if s.count("MMQ") > 1:
        s = "MMQ" + s.rsplit("MMQ", 1)[-1]
    return s


def parse_mmq(raw: str) -> MMQStatus | None:
    """Parse an MMQ response string into MMQStatus."""
    s = _clean_raw(raw)
    if not s.startswith("MMQ"):
        return None

    payload = s[3:].lstrip(",")
    parts = [p for p in payload.split(",") if p != ""]
    if len(parts) < 16:
        return None

    try:
        vals = [int(p) for p in parts[:16]]
    except ValueError:
        return None

    return MMQStatus(
        raw=s,
        status=vals[0],
        elevation=vals[1],
        azimuth=vals[2],
        left_actuator=vals[3],
        right_actuator=vals[4],
        last_preset=vals[5],
        temperature=vals[6],
        tv_state=vals[7],
        last_event_source=vals[8],
        firmware_version=vals[9],
        lost_flag=vals[10],
        tv_current=vals[11],
        left_at_limit=vals[12],
        right_at_limit=vals[13],
        left_motor_current=vals[14],
        right_motor_current=vals[15],
    )


def option_from_preset(preset: int) -> str:
    """Convert a preset number to a select option string."""
    if preset == 0:
        return "Home"
    if preset in (1, 2, 3, 4):
        return f"M{preset}"
    return "Home"

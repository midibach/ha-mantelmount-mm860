"""Constants for MantelMount MM860 integration."""
DOMAIN = "mantelmount_mm860"

DEFAULT_PORT = 81
DEFAULT_TIMEOUT = 2.0
DEFAULT_POLL_INTERVAL = 0.1  # 100ms, matches Windows app
DEFAULT_LOCK_WHILE_MOVING = True

CONF_HOST = "host"
CONF_PORT = "port"
CONF_TIMEOUT = "timeout"
CONF_POLL_INTERVAL = "poll_interval"
CONF_LOCK_WHILE_MOVING = "lock_while_moving"

SERVICE_SEND_COMMAND = "send_command"

ATTR_COMMAND = "command"
ATTR_CRLF = "crlf"
ATTR_READ_REPLY = "read_reply"

# Device info
MANUFACTURER = "MantelMount"
MODEL = "MM860"

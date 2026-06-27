from enum import Enum


class RET(Enum):
    """SmartQA API response codes."""

    OK = (0, "成功")
    ERROR = (1, "请求错误")
    EXCEPTION = (-1, "系统异常")
    SERVICE_UNAVAILABLE = (503, "服务不可用")

    def __init__(self, code: int, msg: str) -> None:
        self._code = code
        self._msg = msg

    @property
    def code(self) -> int:
        return self._code

    @property
    def msg(self) -> str:
        return self._msg


class CommonConstant:
    """Shared constants required by the active SmartQA backend."""

    HTTP = "http://"
    HTTPS = "https://"


DATE_DISPLAY_FMT = "%Y-%m-%d"
TIME_DISPLAY_FMT = "%H:%M:%S"
DATETIME_DISPLAY_FMT = "%Y-%m-%d %H:%M:%S"

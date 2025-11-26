"""枚举定义模块"""

from enum import Enum, IntEnum


class DoorStatus(Enum):
    """门状态"""
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    UNKNOWN = "UNKNOWN"


class LogType(Enum):
    """日志类型"""
    SUCCESS = "success"
    REJECT = "reject"
    SYSTEM = "system"


class K230Function(IntEnum):
    """K230 功能 ID"""
    FACE_DETECTION = 6
    FACE_RECOGNITION = 8


class K230ResponseStatus(Enum):
    """K230 响应状态"""
    OK = "OK"
    PONG = "PONG"
    ERR = "ERR"
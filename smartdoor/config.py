"""配置管理模块"""

import os
import logging
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    """系统配置"""
    
    # 串口配置
    SERIAL_PORT: str = "/dev/ttyUSB0"
    SERIAL_BAUDRATE: int = 115200
    SERIAL_TIMEOUT: float = 0.1
    
    # WebSocket 配置
    WS_SERVER_URL: str = "https://exmeaningsmartdoor.zeabur.app"
    DEVICE_TOKEN: str = "smartdoor_exmeaning"
    
    # 人脸识别配置
    FACE_WINDOW_SECONDS: float = 5.0
    FACE_SCORE_THRESHOLD: int = 80
    
    # 自动关门时间（秒）
    AUTO_CLOSE_DELAY: float = 5.0
    
    # 电机配置
    MOTOR_PUL_PIN: int = 18
    MOTOR_DIR_PIN: int = 23
    MOTOR_PULSES_PER_REV: int = 800
    MOTOR_OPEN_ANGLE: float = 90.0
    MOTOR_MIN_DELAY: float = 0.0005
    MOTOR_MAX_DELAY: float = 0.002
    
    # 日志级别
    LOG_LEVEL: int = logging.INFO


def load_config() -> Config:
    """从环境变量加载配置"""
    return Config(
        SERIAL_PORT=os.getenv("SERIAL_PORT", "/dev/ttyUSB0"),
        SERIAL_BAUDRATE=int(os.getenv("SERIAL_BAUDRATE", "115200")),
        SERIAL_TIMEOUT=float(os.getenv("SERIAL_TIMEOUT", "0.1")),
        WS_SERVER_URL=os.getenv("WS_SERVER_URL", "https://exmeaningsmartdoor.zeabur.app"),
        DEVICE_TOKEN=os.getenv("DEVICE_TOKEN", "smartdoor_exmeaning"),
        FACE_WINDOW_SECONDS=float(os.getenv("FACE_WINDOW_SECONDS", "5.0")),
        FACE_SCORE_THRESHOLD=int(os.getenv("FACE_SCORE_THRESHOLD", "80")),
        AUTO_CLOSE_DELAY=float(os.getenv("AUTO_CLOSE_DELAY", "5.0")),
        MOTOR_PUL_PIN=int(os.getenv("MOTOR_PUL_PIN", "18")),
        MOTOR_DIR_PIN=int(os.getenv("MOTOR_DIR_PIN", "23")),
        MOTOR_PULSES_PER_REV=int(os.getenv("MOTOR_PULSES_PER_REV", "800")),
        MOTOR_OPEN_ANGLE=float(os.getenv("MOTOR_OPEN_ANGLE", "90.0")),
        MOTOR_MIN_DELAY=float(os.getenv("MOTOR_MIN_DELAY", "0.0005")),
        MOTOR_MAX_DELAY=float(os.getenv("MOTOR_MAX_DELAY", "0.002")),
        LOG_LEVEL=getattr(
            logging, 
            os.getenv("LOG_LEVEL", "INFO").upper(), 
            logging.INFO
        ),
    )


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """配置日志"""
    logging.basicConfig(
        level=level,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger("SmartDoor")
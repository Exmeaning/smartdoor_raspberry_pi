#!/usr/bin/env python3
"""
SmartDoor 智能门禁系统入口
"""

import sys
import time
import signal

from .config import load_config, setup_logging
from .controller import SmartDoorController


def main() -> int:
    """主函数"""
    # 加载配置
    config = load_config()
    
    # 配置日志
    logger = setup_logging(config.LOG_LEVEL)
    
    # 打印启动信息
    logger.info("=" * 50)
    logger.info("   SmartDoor 智能门禁系统 v2.0")
    logger.info("=" * 50)
    logger.info(f"串口: {config.SERIAL_PORT} @ {config.SERIAL_BAUDRATE}")
    logger.info(f"服务器: {config.WS_SERVER_URL}")
    logger.info(f"识别阈值: {config.FACE_SCORE_THRESHOLD}%")
    logger.info(f"窗口时长: {config.FACE_WINDOW_SECONDS}s")
    logger.info("=" * 50)
    
    # 创建控制器
    controller = SmartDoorController(config)
    
    # 信号处理
    def signal_handler(sig, frame):
        logger.info("\n收到退出信号")
        controller.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 启动
    try:
        if not controller.start():
            logger.error("控制器启动失败")
            return 1
        
        logger.info("按 Ctrl+C 退出")
        
        # 主循环
        while True:
            time.sleep(1)
    
    except KeyboardInterrupt:
        logger.info("\n收到退出信号")
    
    finally:
        controller.stop()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
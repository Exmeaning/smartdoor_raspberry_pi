#!/usr/bin/env python3
"""
电机测试脚本
"""
import sys
import time
import logging

# 添加项目根目录到 python path
sys.path.append(".")

from smartdoor.motor import StepperMotor

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger("Test")

def main():
    logger.info("开始电机测试...")
    
    # 1. 初始化电机 (使用默认 PIN: PUL=18, DIR=23)
    motor = StepperMotor(
        pul_pin=18,
        dir_pin=23,
        pulses_per_rev=800,
        min_delay=0.0005,
        max_delay=0.002
    )
    
    # 2. 正转 90 度
    time.sleep(1)
    angle = 90
    logger.info(f"Test: 正转 {angle} 度")
    motor.rotate(angle,cw=True)
    
    # 3. 停顿
    logger.info("Test: 等待 2 秒...")
    time.sleep(2)
    
    # 4. 反转 90 度
    logger.info(f"Test: 反转 {angle} 度")
    motor.rotate(angle, cw=False)
    
    # 5. 清理
    motor.cleanup()
    logger.info("测试完成")

if __name__ == "__main__":
    main()

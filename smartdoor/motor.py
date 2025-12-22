"""步进电机控制模块"""

import sys
import time
import logging
import threading
from typing import Optional

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    # 尝试加载系统包 (Pi 5 workaround)
    sys.path.append("/usr/lib/python3/dist-packages")
    try:
        import RPi.GPIO as GPIO
        GPIO_AVAILABLE = True
    except ImportError:
        GPIO_AVAILABLE = False

logger = logging.getLogger("SmartDoor.Motor")


class StepperMotor:
    """步进电机控制器 (共阴接法)"""
    
    def __init__(
        self, 
        pul_pin: int, 
        dir_pin: int, 
        pulses_per_rev: int = 800,
        min_delay: float = 0.0005,  # 2000Hz
        max_delay: float = 0.002    # 500Hz
    ):
        """
        初始化步进电机
        
        Args:
            pul_pin: 脉冲引脚 (BCM)
            dir_pin: 方向引脚 (BCM)
            pulses_per_rev: 每圈脉冲数
            min_delay: 最小脉冲间隔 (最快速度)
            max_delay: 最大脉冲间隔 (起步速度)
        """
        self.pul_pin = pul_pin
        self.dir_pin = dir_pin
        self.ppr = pulses_per_rev
        self.min_delay = min_delay
        self.max_delay = max_delay
        
        self._lock = threading.Lock()
        
        if GPIO_AVAILABLE:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup(self.pul_pin, GPIO.OUT, initial=GPIO.LOW)
            GPIO.setup(self.dir_pin, GPIO.OUT, initial=GPIO.LOW)
        else:
            logger.warning("RPi.GPIO 不可用，使用模拟模式")
            
    def rotate(self, angle: float, cw: bool = True):
        """
        转动指定角度
        
        Args:
            angle: 角度 (度)
            cw: 是否顺时针 (True: CW/Open, False: CCW/Close)
        """
        if angle <= 0:
            return
            
        pulses = int((angle / 360.0) * self.ppr)
        direction_str = "顺时针" if cw else "逆时针"
        logger.info(f"电机转动: {angle}° {direction_str} ({pulses} 脉冲)")
        
        with self._lock:
            if GPIO_AVAILABLE:
                # 设置方向
                # 假设 HIGH 是 CW/Open, LOW 是 CCW/Close，具体根据接线调整
                # 用户提示 "共阴接法，高电平有效" -> 指的是 PUL/DIR 信号本身高电平有效
                # 方向电平取决于驱动器定义，暂时假设 HIGH=CW
                GPIO.output(self.dir_pin, GPIO.HIGH if cw else GPIO.LOW)
                
                # 留出方向建立时间
                time.sleep(0.001)
                
                # 发送脉冲
                self._send_pulses(pulses)
            else:
                time.sleep(1.0)  # 模拟转动时间
                
    def _send_pulses(self, count: int):
        """发送脉冲 (带加减速)"""
        # 简单的梯形加减速
        # 加速段: 前 20%
        # 减速段: 后 20%
        # 匀速段: 中间 60%
        
        ramp_steps = int(count * 0.2)
        if ramp_steps < 5:
            # 脉冲太少，不加减速
            ramp_steps = 0
            
        current_delay = self.max_delay
        delay_step = (self.max_delay - self.min_delay) / (ramp_steps if ramp_steps > 0 else 1)
        
        for i in range(count):
            # 计算当前延迟
            if i < ramp_steps:
                # 加速
                current_delay -= delay_step
            elif i >= count - ramp_steps:
                # 减速
                current_delay += delay_step
            else:
                # 匀速
                current_delay = self.min_delay
                
            # 限制范围
            current_delay = max(self.min_delay, min(self.max_delay, current_delay))
            
            # 发送脉冲 (高电平有效)
            GPIO.output(self.pul_pin, GPIO.HIGH)
            time.sleep(current_delay / 2)
            GPIO.output(self.pul_pin, GPIO.LOW)
            time.sleep(current_delay / 2)

    def cleanup(self):
        """清理 GPIO"""
        if GPIO_AVAILABLE:
            GPIO.cleanup([self.pul_pin, self.dir_pin])

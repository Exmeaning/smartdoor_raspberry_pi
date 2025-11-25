# 电机控制处理器 / Motor Control Handler

from handlers.base_handler import BaseHandler
import logging

logger = logging.getLogger(__name__)


class MotorController:
    """
    电机控制器类 / Motor Controller Class
    用于控制连接到树莓派的电机
    """
    
    def __init__(self, gpio_pins=None):
        """
        初始化电机控制器
        gpio_pins: GPIO引脚配置字典
        """
        self.gpio_pins = gpio_pins or {}
        self.motors = {}
        self._initialized = False
    
    def init(self):
        """初始化GPIO"""
        try:
            import RPi.GPIO as GPIO
            GPIO.setmode(GPIO.BCM)
            
            for motor_name, pins in self.gpio_pins.items():
                for pin in pins.values():
                    GPIO.setup(pin, GPIO.OUT)
                    GPIO.output(pin, GPIO.LOW)
                self.motors[motor_name] = pins
            
            self._initialized = True
            logger.info("Motor controller initialized")
            return True
        
        except Exception as e:
            logger.error(f"Motor init failed: {e}")
            return False
    
    def move(self, motor_name, direction, speed=100):
        """
        控制电机运动
        motor_name: 电机名称
        direction: 方向 ('forward', 'backward', 'stop')
        speed: 速度 (0-100)
        """
        if not self._initialized:
            logger.warning("Motor controller not initialized")
            return False
        
        if motor_name not in self.motors:
            logger.warning(f"Unknown motor: {motor_name}")
            return False
        
        try:
            import RPi.GPIO as GPIO
            pins = self.motors[motor_name]
            
            if direction == 'forward':
                GPIO.output(pins['in1'], GPIO.HIGH)
                GPIO.output(pins['in2'], GPIO.LOW)
            elif direction == 'backward':
                GPIO.output(pins['in1'], GPIO.LOW)
                GPIO.output(pins['in2'], GPIO.HIGH)
            else:  # stop
                GPIO.output(pins['in1'], GPIO.LOW)
                GPIO.output(pins['in2'], GPIO.LOW)
            
            logger.debug(f"Motor {motor_name}: {direction} @ {speed}%")
            return True
        
        except Exception as e:
            logger.error(f"Motor control error: {e}")
            return False
    
    def stop_all(self):
        """停止所有电机"""
        for motor_name in self.motors:
            self.move(motor_name, 'stop')
    
    def cleanup(self):
        """清理GPIO"""
        try:
            import RPi.GPIO as GPIO
            self.stop_all()
            GPIO.cleanup()
            self._initialized = False
            logger.info("Motor controller cleaned up")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")


class FaceTrackingMotorController:
    """
    基于人脸追踪的电机控制器 / Face Tracking Motor Controller
    根据人脸位置控制电机使摄像头跟随人脸
    """
    
    def __init__(self, motor_controller, frame_size=(640, 480)):
        self.motor_controller = motor_controller
        self.frame_width = frame_size[0]
        self.frame_height = frame_size[1]
        
        # 中心区域（死区）
        self.dead_zone_x = 50  # 像素
        self.dead_zone_y = 50
        
        # 帧中心
        self.center_x = self.frame_width // 2
        self.center_y = self.frame_height // 2
    
    def track_face(self, face_data):
        """
        根据人脸位置控制电机
        face_data: 包含 x, y, w, h 的字典
        """
        if not face_data:
            return
        
        x = face_data.get('x', 0)
        y = face_data.get('y', 0)
        w = face_data.get('w', 0)
        h = face_data.get('h', 0)
        
        # 计算人脸中心
        face_center_x = x + w // 2
        face_center_y = y + h // 2
        
        # 计算偏移
        offset_x = face_center_x - self.center_x
        offset_y = face_center_y - self.center_y
        
        # 水平控制（pan）
        if abs(offset_x) > self.dead_zone_x:
            if offset_x > 0:
                self.motor_controller.move('pan', 'forward')
            else:
                self.motor_controller.move('pan', 'backward')
        else:
            self.motor_controller.move('pan', 'stop')
        
        # 垂直控制（tilt）
        if abs(offset_y) > self.dead_zone_y:
            if offset_y > 0:
                self.motor_controller.move('tilt', 'forward')
            else:
                self.motor_controller.move('tilt', 'backward')
        else:
            self.motor_controller.move('tilt', 'stop')
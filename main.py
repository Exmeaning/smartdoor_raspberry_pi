#!/usr/bin/env python3
# 树莓派主程序 / Raspberry Pi Main Program

import time
import logging
import argparse
from threading import Event

from config import FuncID, RunMode
from utils.serial_manager import AsyncSerialManager
from utils.protocol import Protocol
from handlers.face_handler import (
    FaceDetectionHandler,
    FaceRecognitionHandler,
    RegistrationResultHandler,
    StatusHandler,
    ErrorHandler
)
from handlers.motor_handler import MotorController, FaceTrackingMotorController

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class K230Controller:
    """
    K230控制器类 / K230 Controller Class
    管理与K230的通信和数据处理
    """
    
    def __init__(self, serial_port=None, baudrate=None):
        # 初始化协议和串口
        self.protocol = Protocol()
        self.serial = AsyncSerialManager(port=serial_port, baudrate=baudrate)
        
        # 初始化处理器
        self.handlers = {}
        self._init_handlers()
        
        # 电机控制器（可选）
        self.motor_controller = None
        self.face_tracker = None
        
        # 当前模式
        self.current_mode = RunMode.IDLE
        
        # 退出事件
        self.exit_event = Event()
    
    def _init_handlers(self):
        """初始化数据处理器"""
        self.handlers[FuncID.DATA_FACE_DETECT] = FaceDetectionHandler(
            self.protocol,
            callback=self._on_face_detected
        )
        
        self.handlers[FuncID.DATA_FACE_RECOGNITION] = FaceRecognitionHandler(
            self.protocol,
            callback=self._on_face_recognized
        )
        
        self.handlers[FuncID.DATA_REGISTER_RESULT] = RegistrationResultHandler(
            self.protocol,
            callback=self._on_registration_result
        )
        
        self.handlers[FuncID.DATA_STATUS] = StatusHandler(
            self.protocol,
            callback=self._on_status_update
        )
        
        self.handlers[FuncID.DATA_ERROR] = ErrorHandler(
            self.protocol,
            callback=self._on_error
        )
    
    def init_motor_control(self, gpio_pins=None):
        """初始化电机控制"""
        default_pins = {
            'pan': {'in1': 17, 'in2': 18},
            'tilt': {'in1': 22, 'in2': 23}
        }
        
        self.motor_controller = MotorController(gpio_pins or default_pins)
        if self.motor_controller.init():
            self.face_tracker = FaceTrackingMotorController(self.motor_controller)
            logger.info("Motor control initialized")
        else:
            logger.warning("Motor control initialization failed")
    
    # ===== 回调函数 =====
    
    def _on_face_detected(self, data):
        """人脸检测回调"""
        logger.debug(f"Face detected callback: {data}")
        
        # 如果启用了人脸追踪
        if self.face_tracker:
            self.face_tracker.track_face(data)
    
    def _on_face_recognized(self, data):
        """人脸识别回调"""
        if data['is_known']:
            logger.info(f"Welcome, {data['name']}!")
        else:
            logger.info("Unknown person detected")
        
        # 可以在这里添加门禁控制逻辑
        if data['is_known'] and data['score'] > 0.8:
            self._unlock_door()
    
    def _on_registration_result(self, data):
        """注册结果回调"""
        if data['success']:
            logger.info(f"Successfully registered: {data['name']}")
        else:
            logger.error(f"Registration failed: {data['message']}")
    
    def _on_status_update(self, data):
        """状态更新回调"""
        self.current_mode = data['mode']
        logger.info(f"Mode updated: {data['mode']} - {data['message']}")
    
    def _on_error(self, data):
        """错误回调"""
        logger.error(f"K230 Error [{data['code']}]: {data['message']}")
    
    def _unlock_door(self):
        """开门操作（示例）"""
        logger.info("Door unlocked!")
        # 在这里添加实际的开门控制逻辑
    
    # ===== 数据处理 =====
    
    def _process_data(self, raw_data):
        """处理接收到的原始数据"""
        result = self.protocol.parse_data(raw_data)
        
        if result is None:
            return
        
        func_id, data = result
        
        if func_id in self.handlers:
            self.handlers[func_id].handle(data)
        else:
            logger.warning(f"No handler for func_id: {func_id}")
    
    # ===== 命令发送 =====
    
    def switch_mode(self, mode):
        """切换K230运行模式"""
        cmd = self.protocol.build_switch_mode_cmd(mode)
        self.serial.send(cmd)
        logger.info(f"Switching to mode: {mode}")
    
    def start_face_detection(self):
        """启动人脸检测"""
        self.switch_mode(RunMode.FACE_DETECTION)
    
    def start_face_recognition(self):
        """启动人脸识别"""
        self.switch_mode(RunMode.FACE_RECOGNITION)
    
    def register_face(self, user_id, user_name, image_path=None):
        """注册人脸"""
        cmd = self.protocol.build_register_cmd(user_id, user_name, image_path)
        self.serial.send(cmd)
        logger.info(f"Registering face: {user_name}")
    
    def delete_face(self, user_id, user_name):
        """删除人脸"""
        cmd = self.protocol.build_delete_cmd(user_id, user_name)
        self.serial.send(cmd)
        logger.info(f"Deleting face: {user_name}")
    
    def get_status(self):
        """获取K230状态"""
        cmd = self.protocol.build_get_status_cmd()
        self.serial.send(cmd)
    
    def stop(self):
        """停止K230当前任务"""
        cmd = self.protocol.build_stop_cmd()
        self.serial.send(cmd)
        logger.info("Stop command sent")
    
    # ===== 主循环 =====
    
    def start(self):
        """启动控制器"""
        if not self.serial.open():
            logger.error("Failed to open serial port")
            return False
        
            # 注册回调函数
        # SerialManager 在接收到一行数据后会调用此函数
        self.serial.register_callback(self._process_data)
        
        logger.info("K230 Controller started successfully")
        return True

    def cleanup(self):
        """清理资源 / Cleanup resources"""
        logger.info("Stopping controller...")
        self.exit_event.set()
        
        # 关闭串口 (SerialManager.close 会处理线程join)
        if self.serial:
            self.serial.close()
            
        # 停止电机
        if self.motor_controller:
            try:
                # 假设 MotorController 有 stop 方法
                self.motor_controller.stop()
            except Exception as e:
                logger.warning(f"Error stopping motors: {e}")
            
        logger.info("Controller stopped")

    def run(self):
        """
        主运行循环 / Main Loop
        保持主线程运行，并处理异常退出
        """
        if not self.start():
            logger.error("Failed to start controller")
            return

        logger.info("System is running. Press Ctrl+C to exit.")
        
        try:
            # 启动后发送一个获取状态指令，确认连接正常
            self.get_status()
            
            # 主循环，挂起主线程，等待事件或中断
            while not self.exit_event.is_set():
                # 这里可以添加定时任务，例如每隔几秒检查一次心跳
                # 或者检查特定的GPIO状态
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}", exc_info=True)
        finally:
            self.cleanup()

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='Raspberry Pi K230 Controller')
    
    parser.add_argument('--port', type=str, default=None, 
                      help='Serial port device (default: from config)')
    parser.add_argument('--baud', type=int, default=None, 
                      help='Baud rate (default: from config)')
    parser.add_argument('--no-motor', action='store_true', 
                      help='Disable motor control initialization')
    
    return parser.parse_args()

if __name__ == '__main__':
    # 解析参数
    args = parse_args()
    
    # 实例化控制器
    # 如果 args.port 为 None，Controller 内部会使用 config 中的默认值
    controller = K230Controller(
        serial_port=args.port,
        baudrate=args.baud
    )
    
    # 初始化电机（除非通过参数明确禁用）
    if not args.no_motor:
        # 你可以在这里传入自定义的 GPIO 引脚配置
        # controller.init_motor_control(gpio_pins=...)
        controller.init_motor_control()
    
    # 运行主程序
    controller.run()
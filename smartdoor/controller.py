"""主控制器模块"""

import time
import threading
import logging
from typing import Optional

from .config import Config
from .enums import DoorStatus, LogType, K230Function
from .protocol import FaceDetection, FaceRecognition
from .k230_serial import K230Serial
from .websocket_client import WebSocketClient
from .face_manager import FaceRecognitionManager
from .motor import StepperMotor

logger = logging.getLogger("SmartDoor.Ctrl")


class SmartDoorController:
    """智能门控制器"""
    
    def __init__(self, config: Config):
        self.config = config
        self._running = False
        
        # 初始化组件
        self._k230 = K230Serial(
            port=config.SERIAL_PORT,
            baudrate=config.SERIAL_BAUDRATE,
            timeout=config.SERIAL_TIMEOUT
        )
        
        self._ws = WebSocketClient(
            server_url=config.WS_SERVER_URL,
            device_token=config.DEVICE_TOKEN
        )
        
        self._face_manager = FaceRecognitionManager(
            window_duration=config.FACE_WINDOW_SECONDS,
            score_threshold=config.FACE_SCORE_THRESHOLD,
            on_success=self._handle_face_success,
            on_reject=self._handle_face_reject
        )
        
        # 状态
        self._door_status = DoorStatus.CLOSED
        self._close_timer: Optional[threading.Timer] = None
        self._timer_thread: Optional[threading.Thread] = None

        # 电机控制
        self._motor = StepperMotor(
            pul_pin=config.MOTOR_PUL_PIN,
            dir_pin=config.MOTOR_DIR_PIN,
            pulses_per_rev=config.MOTOR_PULSES_PER_REV,
            min_delay=config.MOTOR_MIN_DELAY,
            max_delay=config.MOTOR_MAX_DELAY
        )
    
    @property
    def door_status(self) -> DoorStatus:
        return self._door_status
    
    def start(self) -> bool:
        """启动控制器"""
        logger.info("=" * 50)
        logger.info("SmartDoor 控制器启动中...")
        logger.info("=" * 50)
        
        # 1. 连接 K230
        if not self._k230.connect():
            logger.error("❌ K230 连接失败")
            return False
        
        # 2. 测试通信
        if not self._k230.ping():
            logger.error("❌ K230 PING 失败")
            self._k230.disconnect()
            return False
        
        logger.info("✅ K230 连接正常")
        
        # 3. 设置回调
        self._k230.on_face_detection = self._on_face_detection
        self._k230.on_face_recognition = self._on_face_recognition
        self._ws.on_command = self._on_ws_command
        
        # 4. 启动 WebSocket（异步，不阻塞）
        self._ws.start_async()
        
        # 5. 启动人脸识别
        if self._k230.start_function(K230Function.FACE_RECOGNITION):
            logger.info("✅ 人脸识别已启动")
        else:
            logger.warning("⚠️ 人脸识别启动失败，尝试人脸检测")
            if self._k230.start_function(K230Function.FACE_DETECTION):
                logger.info("✅ 人脸检测已启动")
        
        # 6. 启动定时器
        self._running = True
        self._timer_thread = threading.Thread(
            target=self._timer_loop,
            daemon=True,
            name="Timer"
        )
        self._timer_thread.start()
        
        logger.info("=" * 50)
        logger.info("SmartDoor 控制器已启动")
        logger.info("=" * 50)
        return True
    
    def stop(self):
        """停止控制器"""
        logger.info("SmartDoor 控制器停止中...")
        
        self._running = False
        
        # 取消关门定时器
        if self._close_timer:
            self._close_timer.cancel()
        
        # 停止 K230
        self._k230.stop_function()
        self._k230.disconnect()
        
        # 断开 WebSocket
        self._ws.disconnect()
        
        # 等待定时器线程
        if self._timer_thread:
            self._timer_thread.join(timeout=2.0)
        
        logger.info("SmartDoor 控制器已停止")
    
    def _timer_loop(self):
        """定时器循环"""
        STATUS_INTERVAL = 30  # 状态上报间隔
        last_status_time = 0
        
        while self._running:
            # 检查识别超时
            self._face_manager.check_timeout()
            
            # 定期上报状态
            now = time.time()
            if now - last_status_time >= STATUS_INTERVAL:
                self._report_status()
                last_status_time = now
            
            time.sleep(0.5)
    
    def _report_status(self):
        """上报状态"""
        self._ws.report_door_status(self._door_status)
    
    # ==================== K230 回调 ====================
    
    def _on_face_detection(self, detection: FaceDetection):
        """人脸检测回调"""
        self._face_manager.on_face_detected(detection)
    
    def _on_face_recognition(self, recognition: FaceRecognition):
        """人脸识别回调"""
        logger.debug(f"识别: {recognition.name} ({recognition.score}%)")
        self._face_manager.on_recognition_result(recognition)
    
    # ==================== 识别结果处理 ====================
    
    def _handle_face_success(
        self, 
        user_id: str, 
        recognition: Optional[FaceRecognition]
    ):
        """处理识别成功"""
        self._open_door()
        
        msg = f"识别成功: {user_id}"
        if recognition:
            msg += f" (置信度: {recognition.score}%)"
        
        self._ws.report_log(LogType.SUCCESS, msg)
    
    def _handle_face_reject(
        self, 
        attempt_count: int, 
        recognition: Optional[FaceRecognition]
    ):
        """处理识别失败"""
        msg = f"识别失败: {attempt_count} 次尝试"
        self._ws.report_log(LogType.REJECT, msg)
    
    # ==================== WebSocket 命令处理 ====================
    
    def _on_ws_command(self, data: dict):
        """处理 WebSocket 命令"""
        cmd = data.get("cmd", "")
        logger.info(f"处理命令: {cmd}")
        
        if cmd == "OPEN":
            self._open_door()
            self._ws.report_log(LogType.SYSTEM, "远程开门")
        
        elif cmd == "CLOSE":
            self._close_door()
            self._ws.report_log(LogType.SYSTEM, "远程关门")
        
        elif cmd == "REGISTER_FACE":
            user_id = data.get("user_id", "")
            if user_id:
                threading.Thread(
                    target=self._register_face,
                    args=(user_id,),
                    daemon=True
                ).start()
            else:
                self._ws.report_log(LogType.SYSTEM, "注册失败: 未提供用户ID")
        
        elif cmd == "REFRESH":
            self._report_status()
            
        elif cmd == "SET_CONFIG":
            self._handle_set_config(data)
            
    def _handle_set_config(self, data: dict):
        """处理配置更新"""
        try:
            if "angle" in data:
                angle = float(data["angle"])
                self.config.MOTOR_OPEN_ANGLE = angle
                self._ws.report_log(LogType.SYSTEM, f"配置更新: 开门角度={angle}")
                
            if "speed" in data:
                # 简单处理速度等级：1=慢, 2=中, 3=快
                speed = int(data["speed"])
                # 这里可以根据需要调整 min_delay
                # 暂时只做日志演示
                self._ws.report_log(LogType.SYSTEM, f"配置更新: 速度={speed}")
                
        except Exception as e:
            logger.error(f"配置更新失败: {e}")
            self._ws.report_log(LogType.SYSTEM, f"配置错误: {e}")
    
    # ==================== 门控制 ====================
    
    def _open_door(self):
        """开门"""
        logger.info("🚪 开门")
        
        # 取消之前的关门定时器
        if self._close_timer:
            self._close_timer.cancel()
        
        self._door_status = DoorStatus.OPEN
        self._report_status()
        
        # Motor Open (CW)
        threading.Thread(
            target=self._motor.rotate,
            args=(self.config.MOTOR_OPEN_ANGLE, True),
            daemon=True
        ).start()
        
        # 自动关门
        self._close_timer = threading.Timer(
            self.config.AUTO_CLOSE_DELAY,
            self._close_door
        )
        self._close_timer.start()
    
    def _close_door(self):
        """关门"""
        logger.info("🚪 关门")
        
        self._door_status = DoorStatus.CLOSED
        self._report_status()
        
        # Motor Close (CCW)
        threading.Thread(
            target=self._motor.rotate,
            args=(self.config.MOTOR_OPEN_ANGLE, False),
            daemon=True
        ).start()
    
    # ==================== 人脸注册 ====================
    
    def _register_face(self, user_id: str):
        """注册人脸"""
        logger.info(f"开始注册: {user_id}")
        self._ws.report_log(LogType.SYSTEM, f"开始注册: {user_id}")
        
        # 停止当前功能
        self._k230.stop_function()
        time.sleep(0.5)
        
        # 执行注册
        success = self._k230.register_face(user_id)
        
        if success:
            logger.info(f"✅ 注册成功: {user_id}")
            self._ws.report_log(LogType.SYSTEM, f"注册成功: {user_id}")
        else:
            logger.error(f"❌ 注册失败: {user_id}")
            self._ws.report_log(LogType.SYSTEM, f"注册失败: {user_id}")
        
        # 恢复人脸识别
        time.sleep(0.5)
        self._k230.start_function(K230Function.FACE_RECOGNITION)
"""人脸识别状态机模块"""

import time
import threading
import logging
from dataclasses import dataclass, field
from typing import Optional, Callable

from .protocol import FaceDetection, FaceRecognition

logger = logging.getLogger("SmartDoor.Face")


@dataclass
class RecognitionWindow:
    """识别窗口状态"""
    start_time: float = 0.0
    active: bool = False
    success_reported: bool = False
    failure_count: int = 0
    last_success_user: str = ""
    last_recognition: Optional[FaceRecognition] = None


class FaceRecognitionManager:
    """
    人脸识别管理器
    
    采用滑动窗口机制：
    - 检测到人脸时开启窗口
    - 窗口期内多次识别取最佳结果
    - 成功后只报告一次
    - 窗口超时后报告失败
    """
    
    def __init__(
        self, 
        window_duration: float,
        score_threshold: int,
        on_success: Callable[[str, Optional[FaceRecognition]], None],
        on_reject: Callable[[int, Optional[FaceRecognition]], None]
    ):
        """
        Args:
            window_duration: 识别窗口时长（秒）
            score_threshold: 识别分数阈值
            on_success: 识别成功回调 (user_id, recognition)
            on_reject: 识别失败回调 (attempt_count, last_recognition)
        """
        self.window_duration = window_duration
        self.score_threshold = score_threshold
        self.on_success = on_success
        self.on_reject = on_reject
        
        self._window = RecognitionWindow()
        self._lock = threading.Lock()
    
    def _reset_window(self):
        """重置窗口"""
        self._window = RecognitionWindow()
    
    def _start_window(self):
        """开启新窗口"""
        self._window = RecognitionWindow(
            start_time=time.time(),
            active=True
        )
        logger.debug("开启识别窗口")
    
    def _is_window_expired(self) -> bool:
        """窗口是否已过期"""
        if not self._window.active:
            return True
        return (time.time() - self._window.start_time) >= self.window_duration
    
    def on_face_detected(self, detection: FaceDetection):
        """
        处理人脸检测事件
        
        检测到人脸时，如果没有活跃窗口则开启新窗口
        """
        with self._lock:
            if not self._window.active:
                self._start_window()
    
    def on_recognition_result(self, recognition: FaceRecognition):
        """
        处理识别结果
        
        Args:
            recognition: 识别结果
        """
        with self._lock:
            # 检查窗口是否过期
            if self._is_window_expired():
                # 先处理旧窗口的失败
                if (self._window.active and 
                    not self._window.success_reported and 
                    self._window.failure_count > 0):
                    self._report_reject()
                
                # 开启新窗口
                self._start_window()
            
            # 保存最后一次识别
            self._window.last_recognition = recognition
            
            # 判断是否成功
            is_success = (
                recognition.is_known and 
                recognition.score >= self.score_threshold
            )
            
            if is_success:
                # 成功，且本窗口尚未报告过
                if not self._window.success_reported:
                    self._window.success_reported = True
                    self._window.last_success_user = recognition.name
                    self._report_success(recognition.name)
            else:
                # 失败计数
                self._window.failure_count += 1
    
    def check_timeout(self):
        """
        检查窗口超时
        
        应该在定时器中周期性调用
        """
        with self._lock:
            if self._window.active and self._is_window_expired():
                if not self._window.success_reported and self._window.failure_count > 0:
                    self._report_reject()
                self._reset_window()
    
    def _report_success(self, user_id: str):
        """报告识别成功"""
        logger.info(f"✓ 识别成功: {user_id}")
        try:
            self.on_success(user_id, self._window.last_recognition)
        except Exception as e:
            logger.error(f"成功回调错误: {e}")
    
    def _report_reject(self):
        """报告识别失败"""
        logger.info(f"✗ 识别失败: {self._window.failure_count} 次尝试")
        try:
            self.on_reject(
                self._window.failure_count, 
                self._window.last_recognition
            )
        except Exception as e:
            logger.error(f"失败回调错误: {e}")
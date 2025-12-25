"""K230 串口通信模块"""

import serial
import threading
import time
import logging
from queue import Queue, Empty
from typing import Optional, Callable, List

from .protocol import (
    K230Protocol, 
    K230Response, 
    FaceDetection, 
    FaceRecognition
)
from .enums import K230Function

logger = logging.getLogger("SmartDoor.K230")


class K230Serial:
    """K230 串口通信管理器"""
    
    def __init__(self, port: str, baudrate: int, timeout: float = 0.1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        
        self._serial: Optional[serial.Serial] = None
        self._running = False
        self._rx_buffer = ""
        self._response_queue: Queue = Queue()
        self._lock = threading.Lock()
        self._read_thread: Optional[threading.Thread] = None
        
        # 回调函数
        self.on_face_detection: Optional[Callable[[FaceDetection], None]] = None
        self.on_face_recognition: Optional[Callable[[FaceRecognition], None]] = None
        
        # 调试计数
        self._rx_count = 0
        self._msg_count = 0
    
    @property
    def is_connected(self) -> bool:
        """是否已连接"""
        return self._serial is not None and self._serial.is_open
    
    def connect(self) -> bool:
        """连接串口"""
        try:
            self._serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE
            )
            self._serial.reset_input_buffer()
            self._serial.reset_output_buffer()
            
            self._running = True
            self._read_thread = threading.Thread(
                target=self._read_loop, 
                daemon=True,
                name="K230-Reader"
            )
            self._read_thread.start()
            
            time.sleep(0.5)  # 等待串口稳定
            logger.info(f"K230 串口已连接: {self.port} @ {self.baudrate}")
            logger.debug(f"读取线程状态: {self._read_thread.is_alive()}")
            return True
            
        except Exception as e:
            logger.error(f"K230 串口连接失败: {e}")
            return False
    
    def disconnect(self):
        """断开连接"""
        self._running = False
        
        if self._read_thread:
            self._read_thread.join(timeout=2.0)
            self._read_thread = None
        
        if self._serial:
            try:
                self._serial.close()
            except:
                pass
            self._serial = None
        
        logger.info("K230 串口已断开")
    
    def _read_loop(self):
        """串口读取循环"""
        logger.debug("读取线程已启动")
        
        while self._running and self._serial:
            try:
                if self._serial.in_waiting > 0:
                    data = self._serial.read(self._serial.in_waiting)
                    text = data.decode('utf-8', errors='ignore')
                    self._rx_count += len(data)
                    
                    # 添加原始数据日志
                    logger.debug(f"[RX] 原始数据({len(data)}字节): {repr(text)}")
                    
                    self._process_data(text)
                else:
                    time.sleep(0.01)
            except Exception as e:
                if self._running:
                    logger.error(f"串口读取错误: {e}")
                time.sleep(0.1)
        
        logger.debug("读取线程已退出")
    
    def _process_data(self, data: str):
        """处理接收数据"""
        self._rx_buffer += data
        
        # 显示缓冲区状态
        logger.debug(f"[BUFFER] 当前缓冲区: {repr(self._rx_buffer)}")
        
        while True:
            # 查找消息起始
            start = self._rx_buffer.find('$')
            if start == -1:
                if self._rx_buffer:
                    logger.debug(f"[BUFFER] 丢弃无效数据: {repr(self._rx_buffer)}")
                self._rx_buffer = ""
                break
            
            # 丢弃起始符之前的数据
            if start > 0:
                logger.debug(f"[BUFFER] 丢弃前缀: {repr(self._rx_buffer[:start])}")
                self._rx_buffer = self._rx_buffer[start:]
            
            # 查找消息结束
            end = self._rx_buffer.find('#')
            if end == -1:
                logger.debug(f"[BUFFER] 等待更多数据, 当前: {repr(self._rx_buffer)}")
                break
            
            # 提取完整消息
            message = self._rx_buffer[:end + 1]
            self._rx_buffer = self._rx_buffer[end + 1:]
            self._msg_count += 1
            
            logger.debug(f"[MSG #{self._msg_count}] 完整消息: {message}")
            
            # 解析并分发
            parsed = K230Protocol.parse_message(message)
            if parsed:
                logger.debug(f"[MSG #{self._msg_count}] 解析结果: type={parsed.get('type')}")
                self._dispatch_message(parsed)
            else:
                logger.warning(f"[MSG #{self._msg_count}] 解析失败: {message}")
    
    def _dispatch_message(self, parsed: dict):
        """分发消息"""
        msg_type = parsed.get("type")
        
        if msg_type == "response":
            response = parsed["response"]
            logger.debug(f"[DISPATCH] 响应入队: status={response.status.value}, data={response.data}")
            self._response_queue.put(response)
            logger.debug(f"[DISPATCH] 队列大小: {self._response_queue.qsize()}")
        
        elif msg_type == "face_detection":
            logger.debug(f"[DISPATCH] 人脸检测")
            if self.on_face_detection:
                try:
                    self.on_face_detection(parsed["data"])
                except Exception as e:
                    logger.error(f"人脸检测回调错误: {e}")
        
        elif msg_type == "face_recognition":
            data = parsed["data"]
            logger.debug(f"[DISPATCH] 人脸识别: {data.name} ({data.score}%)")
            if self.on_face_recognition:
                try:
                    self.on_face_recognition(data)
                except Exception as e:
                    logger.error(f"人脸识别回调错误: {e}")
    
    def send_command(
        self, 
        cmd: str, 
        *args, 
        timeout: float = 2.0
    ) -> Optional[K230Response]:
        """发送命令并等待响应"""
        with self._lock:
            if not self._serial:
                logger.error("串口未连接")
                return None
            
            # 检查读取线程状态
            if self._read_thread and not self._read_thread.is_alive():
                logger.error("读取线程已死亡!")
                return None
            
            # 清空旧响应
            old_count = 0
            while not self._response_queue.empty():
                try:
                    self._response_queue.get_nowait()
                    old_count += 1
                except Empty:
                    break
            if old_count > 0:
                logger.debug(f"清空旧响应: {old_count}个")
            
            # 构建并发送命令
            command = K230Protocol.build_command(cmd, *args)
            logger.info(f"[TX] 发送: {command.decode().strip()}")
            
            try:
                self._serial.write(command)
                self._serial.flush()
            except Exception as e:
                logger.error(f"发送失败: {e}")
                return None
            
            # 等待响应
            logger.debug(f"等待响应, 超时={timeout}秒...")
            try:
                response = self._response_queue.get(timeout=timeout)
                logger.info(f"[RX] 响应: status={response.status.value}, data={response.data}")
                return response
            except Empty:
                logger.warning(f"命令超时: {cmd} (队列大小={self._response_queue.qsize()})")
                logger.warning(f"调试信息: RX总字节={self._rx_count}, 消息数={self._msg_count}")
                return None
    
    # ==================== 便捷方法 ====================
    
    def ping(self) -> bool:
        """PING 命令"""
        resp = self.send_command("PING")
        if resp:
            logger.debug(f"PING 响应: is_pong={resp.is_pong}")
        return resp is not None and resp.is_pong
    
    def get_status(self) -> Optional[dict]:
        """获取状态"""
        resp = self.send_command("STATUS")
        if resp and resp.is_ok and len(resp.data) >= 2:
            return {
                "running": resp.data[0] == "1",
                "function_id": int(resp.data[1]) if resp.data[1].isdigit() else 0
            }
        return None
    
    def start_function(self, func_id: int, timeout: float = 10.0) -> bool:
        """
        启动功能
    
        Args:
            func_id: 功能ID
            timeout: 超时时间，K230初始化可能较慢，默认10秒
        """
        resp = self.send_command("START", func_id, timeout=timeout)
        if resp:
            logger.debug(f"START 响应: is_ok={resp.is_ok}")
        return resp is not None and resp.is_ok

    def stop_function(self, timeout: float = 5.0) -> bool:
        """停止功能"""
        resp = self.send_command("STOP", timeout=timeout)
        return resp is not None and resp.is_ok
    
    def register_face(self, user_id: str) -> bool:
        """注册人脸"""
        resp = self.send_command("REGCAM", user_id, timeout=15.0)
        return resp is not None and resp.is_ok
    
    def delete_user(self, user_id: str) -> bool:
        """删除用户"""
        resp = self.send_command("DELETE", user_id)
        return resp is not None and resp.is_ok
    
    def list_users(self) -> List[str]:
        """列出所有用户"""
        resp = self.send_command("LIST")
        if resp and resp.is_ok:
            if len(resp.data) == 1 and ',' in resp.data[0]:
                return resp.data[0].split(',')
            return resp.data
        return []
    
    def reload_database(self, timeout: float = 5.0) -> bool:
        """重新加载数据库"""
        resp = self.send_command("RELOAD", timeout=timeout)
        return resp is not None and resp.is_ok
"""WebSocket 客户端模块"""

import os
import time
import threading
import logging
import socketio
from typing import Optional, Callable

from .enums import DoorStatus, LogType

# 禁用代理（避免 127.0.0.1:7890 报错）
os.environ['http_proxy'] = ''
os.environ['https_proxy'] = ''
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''

logger = logging.getLogger("SmartDoor.WS")


class WebSocketClient:
    """
    WebSocket 客户端
    
    参考示例代码重写，支持自动重连
    """
    
    def __init__(self, server_url: str, device_token: str):
        """
        Args:
            server_url: 服务器地址 (如 https://xxx.zeabur.app)
            device_token: 设备令牌
        """
        self.server_url = server_url
        self.device_token = device_token
        
        self._sio: Optional[socketio.Client] = None
        self._connected = False
        self._should_run = True
        self._reconnect_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        # 命令回调
        self.on_command: Optional[Callable[[dict], None]] = None
    
    @property
    def connected(self) -> bool:
        """是否已连接"""
        return self._connected
    
    def _create_client(self) -> socketio.Client:
        """创建 Socket.IO 客户端"""
        sio = socketio.Client(
            reconnection=False,  # 禁用内置重连，我们自己管理
            logger=False,
            engineio_logger=False
        )
        
        @sio.event
        def connect():
            self._connected = True
            logger.info(f"✅ WebSocket 已连接: {self.server_url}")
        
        @sio.event
        def connect_error(data):
            self._connected = False
            logger.error(f"❌ WebSocket 连接失败: {data}")
        
        @sio.event
        def disconnect():
            self._connected = False
            logger.warning("⚠️ WebSocket 已断开")
            self._schedule_reconnect()
        
        @sio.on('command')
        def handle_command(data):
            logger.info(f"📩 收到指令: {data}")
            if self.on_command:
                try:
                    self.on_command(data)
                except Exception as e:
                    logger.error(f"指令处理错误: {e}")
        
        @sio.on('error')
        def handle_error(data):
            logger.error(f"服务器错误: {data}")
        
        return sio
    
    def connect(self) -> bool:
        """
        连接服务器
        
        Returns:
            是否连接成功
        """
        with self._lock:
            return self._do_connect()
    
    def _do_connect(self) -> bool:
        """实际连接逻辑"""
        try:
            # 清理旧连接
            if self._sio:
                try:
                    self._sio.disconnect()
                except:
                    pass
            
            # 创建新客户端
            self._sio = self._create_client()
            
            logger.info(f"正在连接: {self.server_url}")
            
            # 连接服务器
            self._sio.connect(
                self.server_url,
                auth={
                    'token': self.device_token,
                    'type': 'device'
                },
                transports=['websocket', 'polling']
            )
            
            # 等待连接建立
            time.sleep(0.5)
            
            return self._connected
            
        except socketio.exceptions.ConnectionError as e:
            logger.error(f"连接错误: {e}")
            return False
        except Exception as e:
            logger.error(f"连接异常: {type(e).__name__}: {e}")
            return False
    
    def _schedule_reconnect(self):
        """安排重连"""
        if not self._should_run:
            return
        
        if self._reconnect_thread and self._reconnect_thread.is_alive():
            return
        
        self._reconnect_thread = threading.Thread(
            target=self._reconnect_loop,
            daemon=True,
            name="WS-Reconnect"
        )
        self._reconnect_thread.start()
    
    def _reconnect_loop(self):
        """重连循环"""
        delays = [1, 2, 5, 10, 30, 60]  # 递增延迟
        retry = 0
        
        while self._should_run and not self._connected:
            delay = delays[min(retry, len(delays) - 1)]
            logger.info(f"将在 {delay} 秒后重连...")
            time.sleep(delay)
            
            if not self._should_run:
                break
            
            retry += 1
            logger.info(f"尝试重连 (第 {retry} 次)...")
            
            with self._lock:
                if self._do_connect():
                    logger.info("✅ 重连成功")
                    break
    
    def start_async(self):
        """异步启动连接（非阻塞）"""
        threading.Thread(
            target=self._async_connect,
            daemon=True,
            name="WS-Connect"
        ).start()
    
    def _async_connect(self):
        """异步连接"""
        if not self.connect():
            self._schedule_reconnect()
    
    def disconnect(self):
        """断开连接"""
        self._should_run = False
        self._connected = False
        
        if self._sio:
            try:
                self._sio.disconnect()
            except:
                pass
            self._sio = None
        
        logger.info("WebSocket 已关闭")
    
    def wait(self):
        """等待连接关闭（阻塞）"""
        if self._sio:
            try:
                self._sio.wait()
            except:
                pass
    
    # ==================== 消息发送 ====================
    
    def report_door_status(self, status: DoorStatus):
        """上报门状态"""
        if not self._connected or not self._sio:
            return
        
        try:
            self._sio.emit('door_status', status.value)
            logger.debug(f"上报门状态: {status.value}")
        except Exception as e:
            logger.error(f"上报门状态失败: {e}")
    
    def report_log(
        self, 
        log_type: LogType, 
        msg: str, 
        image: str = ""
    ):
        """
        上报日志
        
        Args:
            log_type: 日志类型
            msg: 消息内容
            image: 可选的 base64 图片
        """
        if not self._connected or not self._sio:
            return
        
        try:
            data = {
                'type': log_type.value,
                'msg': msg
            }
            
            if image:
                if not image.startswith('data:'):
                    data['image'] = f"data:image/jpeg;base64,{image}"
                else:
                    data['image'] = image
            
            self._sio.emit('report', data)
            logger.debug(f"上报日志: [{log_type.value}] {msg}")
        except Exception as e:
            logger.error(f"上报日志失败: {e}")
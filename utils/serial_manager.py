# 串口管理器 / Serial Manager

import serial
import threading
import queue
import time
from config import SERIAL_PORT, SERIAL_BAUDRATE, SERIAL_TIMEOUT


class SerialManager:
    """
    串口管理类 / Serial Manager Class
    提供异步读写功能
    """
    
    def __init__(self, port=None, baudrate=None, timeout=None):
        self.port = port or SERIAL_PORT
        self.baudrate = baudrate or SERIAL_BAUDRATE
        self.timeout = timeout or SERIAL_TIMEOUT
        
        self.serial = None
        self.running = False
        
        # 接收队列
        self.rx_queue = queue.Queue()
        
        # 接收线程
        self.rx_thread = None
        
        # 回调函数
        self.callbacks = []
    
    def open(self):
        """打开串口"""
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout
            )
            self.running = True
            
            # 启动接收线程
            self.rx_thread = threading.Thread(target=self._rx_loop, daemon=True)
            self.rx_thread.start()
            
            print(f"Serial port opened: {self.port} @ {self.baudrate}")
            return True
        
        except Exception as e:
            print(f"Failed to open serial port: {e}")
            return False
    
    def close(self):
        """关闭串口"""
        self.running = False
        
        if self.rx_thread and self.rx_thread.is_alive():
            self.rx_thread.join(timeout=1.0)
        
        if self.serial and self.serial.is_open:
            self.serial.close()
        
        print("Serial port closed")
    
    def send(self, data):
        """发送数据"""
        if not self.serial or not self.serial.is_open:
            print("Serial port not open")
            return False
        
        try:
            if isinstance(data, str):
                data = data.encode('utf-8')
            
            self.serial.write(data)
            self.serial.flush()
            return True
        
        except Exception as e:
            print(f"Send error: {e}")
            return False
    
    def read(self, timeout=None):
        """
        读取一条数据
        返回: 数据或None
        """
        try:
            return self.rx_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def read_all(self):
        """读取所有缓存的数据"""
        data_list = []
        while not self.rx_queue.empty():
            try:
                data_list.append(self.rx_queue.get_nowait())
            except queue.Empty:
                break
        return data_list
    
    def register_callback(self, callback):
        """注册数据接收回调函数"""
        self.callbacks.append(callback)
    
    def unregister_callback(self, callback):
        """注销回调函数"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)
    
    def _rx_loop(self):
        """接收线程循环"""
        buffer = b''
        
        while self.running:
            try:
                if self.serial.in_waiting:
                    data = self.serial.readline()
                    if data:
                        # 放入队列
                        self.rx_queue.put(data.rstrip(b'\n'))
                        
                        # 调用回调
                        for callback in self.callbacks:
                            try:
                                callback(data.rstrip(b'\n'))
                            except Exception as e:
                                print(f"Callback error: {e}")
                else:
                    time.sleep(0.01)
            
            except Exception as e:
                if self.running:
                    print(f"RX error: {e}")
                time.sleep(0.1)
    
    @property
    def is_open(self):
        """检查串口是否打开"""
        return self.serial and self.serial.is_open


class AsyncSerialManager(SerialManager):
    """
    异步串口管理器 / Async Serial Manager
    提供事件驱动的接口
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 事件处理器
        self.event_handlers = {}
    
    def on(self, event_name, handler):
        """注册事件处理器"""
        if event_name not in self.event_handlers:
            self.event_handlers[event_name] = []
        self.event_handlers[event_name].append(handler)
    
    def off(self, event_name, handler=None):
        """注销事件处理器"""
        if event_name in self.event_handlers:
            if handler:
                self.event_handlers[event_name].remove(handler)
            else:
                self.event_handlers[event_name] = []
    
    def emit(self, event_name, *args, **kwargs):
        """触发事件"""
        if event_name in self.event_handlers:
            for handler in self.event_handlers[event_name]:
                try:
                    handler(*args, **kwargs)
                except Exception as e:
                    print(f"Event handler error: {e}")
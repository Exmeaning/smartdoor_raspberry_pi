# 基础处理器 / Base Handler

from abc import ABC, abstractmethod


class BaseHandler(ABC):
    """
    数据处理器基类 / Base Data Handler Class
    """
    
    def __init__(self, protocol):
        self.protocol = protocol
    
    @abstractmethod
    def handle(self, data):
        """
        处理接收到的数据
        参数: data - 解析后的数据字典
        """
        pass
    
    @abstractmethod
    def get_func_ids(self):
        """
        返回此处理器处理的功能ID列表
        """
        pass
# 人脸相关处理器 / Face Related Handlers

from handlers.base_handler import BaseHandler
from config import FuncID
import logging

logger = logging.getLogger(__name__)


class FaceDetectionHandler(BaseHandler):
    """人脸检测数据处理器"""
    
    def __init__(self, protocol, callback=None):
        super().__init__(protocol)
        self.callback = callback
        self.last_detection = None
    
    def handle(self, data):
        """处理人脸检测数据"""
        x = data.get('x', -1)
        y = data.get('y', -1)
        w = data.get('w', -1)
        h = data.get('h', -1)
        
        self.last_detection = {
            'x': x, 'y': y, 'w': w, 'h': h,
            'center_x': x + w // 2,
            'center_y': y + h // 2,
            'area': w * h
        }
        
        logger.info(f"Face detected: x={x}, y={y}, w={w}, h={h}")
        
        if self.callback:
            self.callback(self.last_detection)
        
        return self.last_detection
    
    def get_func_ids(self):
        return [FuncID.DATA_FACE_DETECT]
    
    def get_last_detection(self):
        return self.last_detection


class FaceRecognitionHandler(BaseHandler):
    """人脸识别数据处理器"""
    
    def __init__(self, protocol, callback=None):
        super().__init__(protocol)
        self.callback = callback
        self.last_recognition = None
        self.recognized_faces = {}  # 存储识别到的人脸信息
    
    def handle(self, data):
        """处理人脸识别数据"""
        x = data.get('x', -1)
        y = data.get('y', -1)
        w = data.get('w', -1)
        h = data.get('h', -1)
        name = data.get('name', 'unknown')
        score = data.get('score', 0)
        
        self.last_recognition = {
            'x': x, 'y': y, 'w': w, 'h': h,
            'name': name,
            'score': score,
            'is_known': name != 'unknown'
        }
        
        # 更新识别记录
        if name != 'unknown':
            self.recognized_faces[name] = {
                'last_seen': True,
                'score': score,
                'position': (x, y, w, h)
            }
        
        logger.info(f"Face recognized: {name} (score: {score:.2f})")
        
        if self.callback:
            self.callback(self.last_recognition)
        
        return self.last_recognition
    
    def get_func_ids(self):
        return [FuncID.DATA_FACE_RECOGNITION]
    
    def get_last_recognition(self):
        return self.last_recognition
    
    def get_recognized_faces(self):
        return self.recognized_faces
    
    def clear_recognized_faces(self):
        self.recognized_faces = {}


class RegistrationResultHandler(BaseHandler):
    """注册结果处理器"""
    
    def __init__(self, protocol, callback=None):
        super().__init__(protocol)
        self.callback = callback
        self.last_result = None
    
    def handle(self, data):
        """处理注册结果"""
        success = data.get('success', False)
        name = data.get('name', '')
        message = data.get('message', '')
        
        self.last_result = {
            'success': success,
            'name': name,
            'message': message
        }
        
        if success:
            logger.info(f"Registration successful: {name}")
        else:
            logger.warning(f"Registration failed: {name} - {message}")
        
        if self.callback:
            self.callback(self.last_result)
        
        return self.last_result
    
    def get_func_ids(self):
        return [FuncID.DATA_REGISTER_RESULT]


class StatusHandler(BaseHandler):
    """状态处理器"""
    
    def __init__(self, protocol, callback=None):
        super().__init__(protocol)
        self.callback = callback
        self.current_status = None
    
    def handle(self, data):
        """处理状态数据"""
        mode = data.get('mode', 0)
        message = data.get('message', '')
        
        self.current_status = {
            'mode': mode,
            'message': message
        }
        
        logger.info(f"Status update: mode={mode}, message={message}")
        
        if self.callback:
            self.callback(self.current_status)
        
        return self.current_status
    
    def get_func_ids(self):
        return [FuncID.DATA_STATUS]


class ErrorHandler(BaseHandler):
    """错误处理器"""
    
    def __init__(self, protocol, callback=None):
        super().__init__(protocol)
        self.callback = callback
        self.errors = []
    
    def handle(self, data):
        """处理错误数据"""
        code = data.get('code', -1)
        message = data.get('message', '')
        
        error = {
            'code': code,
            'message': message
        }
        
        self.errors.append(error)
        
        logger.error(f"K230 Error [{code}]: {message}")
        
        if self.callback:
            self.callback(error)
        
        return error
    
    def get_func_ids(self):
        return [FuncID.DATA_ERROR]
    
    def get_errors(self):
        return self.errors
    
    def clear_errors(self):
        self.errors = []
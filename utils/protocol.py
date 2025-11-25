# 协议处理类 / Protocol Handler Class

from config import FuncID


class Protocol:
    """
    通信协议类 / Communication Protocol Class
    协议格式: $长度,功能ID,数据1,数据2,...#
    """
    
    def __init__(self):
        self.START_CHAR = '$'
        self.END_CHAR = '#'
        self.SEPARATOR = ','
    
    def _build_packet(self, func_id, *args):
        """构建数据包"""
        data_parts = [str(func_id)]
        for arg in args:
            data_parts.append(str(arg))
        
        data_str = self.SEPARATOR.join(data_parts)
        temp_len = len(data_str) + 3
        
        for i in range(5):
            full_str = f"{self.START_CHAR}{temp_len}{self.SEPARATOR}{data_str}{self.END_CHAR}"
            if len(full_str) == temp_len:
                break
            temp_len = len(full_str)
        
        return (full_str + '\n').encode('utf-8')
    
    # ===== 命令构建 =====
    
    def build_switch_mode_cmd(self, mode):
        """构建切换模式命令"""
        return self._build_packet(FuncID.CMD_SWITCH_MODE, mode)
    
    def build_register_cmd(self, user_id, user_name, image_path=None):
        """构建注册命令"""
        if image_path:
            return self._build_packet(FuncID.CMD_REGISTER_FACE, user_id, user_name, image_path)
        else:
            return self._build_packet(FuncID.CMD_REGISTER_FACE, user_id, user_name)
    
    def build_delete_cmd(self, user_id, user_name):
        """构建删除命令"""
        return self._build_packet(FuncID.CMD_DELETE_FACE, user_id, user_name)
    
    def build_get_status_cmd(self):
        """构建获取状态命令"""
        return self._build_packet(FuncID.CMD_GET_STATUS)
    
    def build_stop_cmd(self):
        """构建停止命令"""
        return self._build_packet(FuncID.CMD_STOP)
    
    # ===== 数据解析 =====
    
    def parse_data(self, data):
        """
        解析接收到的数据
        返回: (func_id, 解析后的数据字典) 或 None
        """
        try:
            if isinstance(data, bytes):
                data = data.decode('utf-8').strip()
            
            if not data.startswith(self.START_CHAR) or not data.endswith(self.END_CHAR):
                return None
            
            content = data[1:-1]
            parts = content.split(self.SEPARATOR)
            
            if len(parts) < 2:
                return None
            
            data_len = int(parts[0])
            func_id = int(parts[1])
            
            if data_len != len(data):
                print(f"Length mismatch: expected {data_len}, got {len(data)}")
                return None
            
            params = parts[2:] if len(parts) > 2 else []
            
            # 根据功能ID解析数据
            return self._parse_by_func_id(func_id, params)
        
        except Exception as e:
            print(f"Parse error: {e}")
            return None
    
    def _parse_by_func_id(self, func_id, params):
        """根据功能ID解析参数"""
        if func_id == FuncID.DATA_FACE_DETECT:
            return self._parse_face_detect(func_id, params)
        
        elif func_id == FuncID.DATA_FACE_RECOGNITION:
            return self._parse_face_recognition(func_id, params)
        
        elif func_id == FuncID.DATA_STATUS:
            return self._parse_status(func_id, params)
        
        elif func_id == FuncID.DATA_REGISTER_RESULT:
            return self._parse_register_result(func_id, params)
        
        elif func_id == FuncID.DATA_ERROR:
            return self._parse_error(func_id, params)
        
        else:
            return (func_id, {'raw_params': params})
    
    def _parse_face_detect(self, func_id, params):
        """解析人脸检测数据"""
        if len(params) < 4:
            return None
        return (func_id, {
            'x': int(params[0]),
            'y': int(params[1]),
            'w': int(params[2]),
            'h': int(params[3])
        })
    
    def _parse_face_recognition(self, func_id, params):
        """解析人脸识别数据"""
        if len(params) < 6:
            return None
        return (func_id, {
            'x': int(params[0]),
            'y': int(params[1]),
            'w': int(params[2]),
            'h': int(params[3]),
            'name': params[4],
            'score': float(params[5]) if params[5] else 0
        })
    
    def _parse_status(self, func_id, params):
        """解析状态数据"""
        if len(params) < 2:
            return None
        return (func_id, {
            'mode': int(params[0]),
            'message': params[1]
        })
    
    def _parse_register_result(self, func_id, params):
        """解析注册结果"""
        if len(params) < 3:
            return None
        return (func_id, {
            'success': params[0] == '1',
            'name': params[1],
            'message': params[2]
        })
    
    def _parse_error(self, func_id, params):
        """解析错误数据"""
        if len(params) < 2:
            return None
        return (func_id, {
            'code': int(params[0]),
            'message': params[1]
        })
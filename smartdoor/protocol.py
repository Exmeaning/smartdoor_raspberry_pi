"""K230 串口协议模块"""

from dataclasses import dataclass
from typing import Optional, List
from .enums import K230ResponseStatus


# ==================== 数据结构 ====================

@dataclass
class FaceDetection:
    """人脸检测结果"""
    x: int
    y: int
    w: int
    h: int


@dataclass
class FaceRecognition:
    """人脸识别结果"""
    x: int
    y: int
    w: int
    h: int
    name: str
    score: int
    
    @property
    def is_known(self) -> bool:
        """是否为已知人脸"""
        return self.name != "unknown" and self.score > 0


@dataclass
class K230Response:
    """
    K230 响应结构
    
    格式: $RSP,<len>,<status>,<data...>#
    示例:
      - $RSP,18,PONG,K230#
      - $RSP,15,OK,0,0#
      - $RSP,21,OK,Started:6#
      - $RSP,25,ERR,Unknown:XXX#
    """
    length: int
    status: K230ResponseStatus
    data: List[str]
    
    @property
    def is_ok(self) -> bool:
        return self.status == K230ResponseStatus.OK
    
    @property
    def is_pong(self) -> bool:
        return self.status == K230ResponseStatus.PONG
    
    @property
    def is_error(self) -> bool:
        return self.status == K230ResponseStatus.ERR
    
    @property
    def error_message(self) -> str:
        """获取错误信息"""
        if self.is_error and self.data:
            return self.data[0]
        return ""


# ==================== 协议解析 ====================

class K230Protocol:
    """
    K230 串口协议处理
    
    命令格式: $CMD,<cmd>[,<args>...]#
    响应格式: $RSP,<len>,<status>,<data...>#
    数据格式: $<len>,<type>,<data...>#
    """
    
    # 数据包类型标识
    DATA_TYPE_FACE_DETECTION = "06"
    DATA_TYPE_FACE_RECOGNITION = "08"
    
    @staticmethod
    def build_command(cmd: str, *args) -> bytes:
        """
        构建命令
        
        Args:
            cmd: 命令名 (PING, STATUS, START, STOP, etc.)
            *args: 命令参数
        
        Returns:
            编码后的命令字节
        """
        if args:
            payload = f"$CMD,{cmd},{','.join(str(a) for a in args)}#"
        else:
            payload = f"$CMD,{cmd}#"
        return payload.encode('utf-8')
    
    @classmethod
    def parse_message(cls, data: str) -> Optional[dict]:
        """
        解析消息
        
        Args:
            data: 原始消息字符串
        
        Returns:
            解析后的字典，包含 type 和相关数据
            - {"type": "response", "response": K230Response}
            - {"type": "face_detection", "data": FaceDetection}
            - {"type": "face_recognition", "data": FaceRecognition}
            - None 表示解析失败
        """
        data = data.strip()
        
        # 验证消息格式
        if not data.startswith('$') or not data.endswith('#'):
            return None
        
        content = data[1:-1]  # 去掉 $ 和 #
        parts = content.split(',')
        
        if len(parts) < 2:
            return None
        
        first = parts[0]
        
        # ===== 响应消息 =====
        if first == "RSP":
            return cls._parse_response(parts)
        
        # ===== 数据包 =====
        if first.isdigit():
            return cls._parse_data_packet(parts)
        
        return None
    
    @classmethod
    def _parse_response(cls, parts: List[str]) -> Optional[dict]:
        """
        解析响应消息
        
        格式: RSP,<len>,<status>,<data...>
        """
        if len(parts) < 3:
            return None
        
        try:
            length = int(parts[1])
            status_str = parts[2].upper()
            
            # 解析状态
            try:
                status = K230ResponseStatus(status_str)
            except ValueError:
                status = K230ResponseStatus.ERR
            
            resp_data = parts[3:] if len(parts) > 3 else []
            
            return {
                "type": "response",
                "response": K230Response(
                    length=length,
                    status=status,
                    data=resp_data
                )
            }
        except ValueError:
            return None
    
    @classmethod
    def _parse_data_packet(cls, parts: List[str]) -> Optional[dict]:
        """
        解析数据包
        
        人脸检测: <len>,06,<x>,<y>,<w>,<h>
        人脸识别: <len>,08,<x>,<y>,<w>,<h>,<name>,<score>
        """
        try:
            # length = int(parts[0])  # 长度字段，可用于校验
            data_type = parts[1] if len(parts) > 1 else ""
            
            # 人脸检测
            if data_type == cls.DATA_TYPE_FACE_DETECTION:
                if len(parts) >= 6:
                    return {
                        "type": "face_detection",
                        "data": FaceDetection(
                            x=int(parts[2]),
                            y=int(parts[3]),
                            w=int(parts[4]),
                            h=int(parts[5])
                        )
                    }
            
            # 人脸识别
            elif data_type == cls.DATA_TYPE_FACE_RECOGNITION:
                if len(parts) >= 8:
                    return {
                        "type": "face_recognition",
                        "data": FaceRecognition(
                            x=int(parts[2]),
                            y=int(parts[3]),
                            w=int(parts[4]),
                            h=int(parts[5]),
                            name=parts[6],
                            score=int(parts[7])
                        )
                    }
        except (ValueError, IndexError):
            pass
        
        return None
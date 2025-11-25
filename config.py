# 树莓派配置文件 / Raspberry Pi Configuration File

# 串口配置 / Serial Configuration
SERIAL_PORT = "/dev/ttyUSB0"  # 或 /dev/ttyAMA0
SERIAL_BAUDRATE = 115200
SERIAL_TIMEOUT = 0.1

# 功能ID定义（与K230保持一致）/ Function ID Definition
class FuncID:
    # 命令ID（树莓派 -> K230）
    CMD_SWITCH_MODE = 1
    CMD_REGISTER_FACE = 2
    CMD_DELETE_FACE = 3
    CMD_GET_STATUS = 4
    CMD_STOP = 5
    
    # 数据ID（K230 -> 树莓派）
    DATA_FACE_DETECT = 6
    DATA_FACE_RECOGNITION = 8
    DATA_STATUS = 10
    DATA_REGISTER_RESULT = 11
    DATA_ERROR = 99

# 运行模式 / Running Mode
class RunMode:
    IDLE = 0
    FACE_DETECTION = 1
    FACE_RECOGNITION = 2
    FACE_REGISTRATION = 3

# 日志配置 / Logging Configuration
LOG_LEVEL = "INFO"
LOG_FILE = "/var/log/k230_comm.log"
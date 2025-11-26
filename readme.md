# SmartDoor 智能门禁系统

```markdown
# SmartDoor 智能门禁系统

基于 K230 人脸识别模块的智能门禁系统，支持本地人脸识别与云端远程控制。

## 📋 项目概述

本项目是一个完整的智能门禁解决方案，运行于树莓派/Linux 设备上，通过串口与 K230 人脸识别模块通信，同时通过 WebSocket 连接云端服务器实现远程控制和状态同步。

### 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         云端服务器                               │
│                  (WebSocket Server)                             │
└─────────────────────────┬───────────────────────────────────────┘
                          │ WebSocket
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    树莓派 / Linux 主机                           │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                  SmartDoor 控制程序                        │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐   │  │
│  │  │ K230Serial  │  │ FaceManager │  │ WebSocketClient │   │  │
│  │  └──────┬──────┘  └─────────────┘  └─────────────────┘   │  │
│  └─────────┼─────────────────────────────────────────────────┘  │
│            │ 串口 (UART)                                        │
└────────────┼────────────────────────────────────────────────────┘
             ▼
┌─────────────────────┐      ┌─────────────────────┐
│   K230 人脸识别模块  │      │   电机/门锁控制模块  │
│   - 人脸检测        │      │   (GPIO - 预留)     │
│   - 人脸识别        │      │                     │
│   - 人脸注册        │      │                     │
└─────────────────────┘      └─────────────────────┘
```

## ✨ 功能特性

### 已实现功能

- ✅ **K230 串口通信** - 完整的协议解析和命令收发
- ✅ **人脸检测** - 实时检测画面中的人脸
- ✅ **人脸识别** - 识别已注册用户并返回置信度
- ✅ **人脸注册** - 通过摄像头注册新用户
- ✅ **滑动窗口识别** - 多帧识别取最优结果，避免误判
- ✅ **WebSocket 通信** - 与云端服务器实时同步
- ✅ **远程开门** - 通过云端下发开门指令
- ✅ **自动重连** - WebSocket 断线自动重连
- ✅ **状态上报** - 定期上报门状态和识别日志

### 预留功能

- 🔧 **电机/门锁控制** - GPIO 控制接口已预留，待硬件到位后实现
- 🔧 **门磁传感器** - 检测门开关状态 （可选，若需要）

## 🔧 硬件要求

| 组件 | 型号/规格 | 状态 |
|------|----------|------|
| 主控 | 树莓派 4B / 任意 Linux 设备 | ✅ |
| 人脸识别 | K230 开发板 | ✅ |
| 串口连接 | USB-TTL 或 GPIO UART | ✅ |
| 电机/门锁 | 电磁锁/舵机 | 🔧 待接入 |
| 电源 | 5V/12V 电源 | 🔧 待接入（可选） |

### 接线说明

**K230 串口连接：**
```
K230 TX  →  主机 RX (USB-TTL 或 GPIO)
K230 RX  →  主机 TX
K230 GND →  主机 GND
```

**电机控制预留 (GPIO)：**
```
GPIO 17 → 继电器/电机驱动 IN (待实现)
GND     → 继电器/电机驱动 GND
```

## 📦 安装部署

### 1. 克隆项目

```bash
git clone https://github.com/yourusername/smartdoor.git
cd smartdoor
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

或手动安装：

```bash
pip install pyserial python-socketio python-dotenv
```

### 3. 配置环境变量

创建 `.env` 文件：

```env
# 串口配置
SERIAL_PORT=/dev/ttyUSB0
SERIAL_BAUDRATE=115200
SERIAL_TIMEOUT=0.1

# WebSocket 配置
WS_SERVER_URL=https://your-server.com
DEVICE_TOKEN=your_device_token

# 人脸识别配置
FACE_WINDOW_SECONDS=5.0
FACE_SCORE_THRESHOLD=80

# 自动关门延迟（秒）
AUTO_CLOSE_DELAY=5.0

# 日志级别 (DEBUG/INFO/WARNING/ERROR)
LOG_LEVEL=INFO
```

### 4. 运行程序

```bash
python run.py
```

或使用模块方式：

```bash
python -m smartdoor.main
```

## 📁 项目结构

```
smartdoor/
├── run.py                  # 启动脚本
├── requirements.txt        # 依赖列表
├── .env                    # 环境变量配置
├── README.md               # 项目说明
└── smartdoor/
    ├── __init__.py         # 包初始化
    ├── main.py             # 主入口
    ├── config.py           # 配置管理
    ├── enums.py            # 枚举定义
    ├── protocol.py         # K230 协议解析
    ├── k230_serial.py      # K230 串口通信
    ├── face_manager.py     # 人脸识别状态机
    ├── websocket_client.py # WebSocket 客户端
    └── controller.py       # 主控制器
```

## 📡 K230 通信协议

### 命令格式

```
发送: $CMD,<命令>[,<参数>...]#
响应: $RSP,<长度>,<状态>,<数据...>#
```

### 支持的命令

| 命令 | 格式 | 说明 |
|------|------|------|
| PING | `$CMD,PING#` | 心跳检测 |
| STATUS | `$CMD,STATUS#` | 获取状态 |
| START | `$CMD,START,<功能ID>#` | 启动功能 (6=检测, 8=识别) |
| STOP | `$CMD,STOP#` | 停止当前功能 |
| REGCAM | `$CMD,REGCAM,<用户ID>#` | 注册人脸 |
| DELETE | `$CMD,DELETE,<用户ID>#` | 删除用户 |
| LIST | `$CMD,LIST#` | 列出用户 |
| RELOAD | `$CMD,RELOAD#` | 重载数据库 |

### 数据上报格式

**人脸检测：**
```
$<长度>,06,<x>,<y>,<w>,<h>#
```

**人脸识别：**
```
$<长度>,08,<x>,<y>,<w>,<h>,<用户名>,<置信度>#
```

## 🔌 预留接口说明

### 电机/门锁控制

在 `controller.py` 中已预留 GPIO 控制接口：

```python
def _open_door(self):
    """开门"""
    logger.info("🚪 开门")
    
    self._door_status = DoorStatus.OPEN
    self._report_status()
    
    # TODO: GPIO 控制 - 待硬件到位后实现
    # import RPi.GPIO as GPIO
    # GPIO.setmode(GPIO.BCM)
    # GPIO.setup(17, GPIO.OUT)
    # GPIO.output(17, GPIO.HIGH)
    
    # 自动关门定时器
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
    
    # TODO: GPIO 控制
    # GPIO.output(17, GPIO.LOW)
```

### 扩展建议

待硬件到位后，可按以下方式扩展：

1. **添加 GPIO 控制模块** `gpio_controller.py`
2. **添加门磁传感器监听** （可选 若需要）
3. **添加蜂鸣器/指示灯反馈**

## 🌐 WebSocket 事件

### 上行事件 (设备 → 服务器)

| 事件 | 数据 | 说明 |
|------|------|------|
| `door_status` | `"OPEN"` / `"CLOSED"` | 门状态 |
| `report` | `{type, msg, image?}` | 日志上报 |

### 下行事件 (服务器 → 设备)

| 事件 | 数据 | 说明 |
|------|------|------|
| `command` | `{cmd: "OPEN"}` | 开门指令 |
| `command` | `{cmd: "CLOSE"}` | 关门指令 |
| `command` | `{cmd: "REGISTER_FACE", user_id: "xxx"}` | 注册人脸 |
| `command` | `{cmd: "REFRESH"}` | 刷新状态 |

## 📝 日志示例

```
2025-11-26 17:00:00 [INFO] SmartDoor: ==================================================
2025-11-26 17:00:00 [INFO] SmartDoor:    SmartDoor 智能门禁系统 v2.0
2025-11-26 17:00:00 [INFO] SmartDoor: ==================================================
2025-11-26 17:00:00 [INFO] SmartDoor: 串口: /dev/ttyUSB0 @ 115200
2025-11-26 17:00:00 [INFO] SmartDoor: 服务器: https://xxx.zeabur.app
2025-11-26 17:00:01 [INFO] SmartDoor.K230: K230 串口已连接: /dev/ttyUSB0 @ 115200
2025-11-26 17:00:01 [INFO] SmartDoor.Ctrl: ✅ K230 连接正常
2025-11-26 17:00:08 [INFO] SmartDoor.Ctrl: ✅ 人脸识别已启动
2025-11-26 17:00:08 [INFO] SmartDoor.WS: ✅ WebSocket 已连接
2025-11-26 17:00:10 [INFO] SmartDoor.Face: ✓ 识别成功: user001
2025-11-26 17:00:10 [INFO] SmartDoor.Ctrl: 🚪 开门
```

## 🛠️ 开发计划

- [x] K230 串口通信
- [x] 人脸识别状态机
- [x] WebSocket 云端通信
- [x] 远程控制功能
- [ ] GPIO 电机控制
- [ ] 门磁状态检测
- [ ] 本地 Web 管理界面
- [ ] 离线模式支持

## 📄 许可证

MIT License

```

---

## requirements.txt

```txt
pyserial>=3.5
python-socketio>=5.0.0
python-dotenv>=1.0.0
```

import serial
import time

# 检查设备号，可能是 /dev/ttyUSB0 或 /dev/ttyACM0
com = "/dev/ttyUSB0" 

try:
    # 尝试打开串口
    ser = serial.Serial(com, 115200, timeout=1)
    print(f"成功打开串口: {com}")
except Exception as e:
    print(f"串口打开失败: {e}")
    exit()

FUNC_ID = 6

def parse_data(data):
    # ... (这里复制之前的 parse_data 函数内容) ...
    if data[0] == ord('$') and data[len(data)-1] == ord('#'):
        try:
            data_list = data[1:len(data)-1].decode('utf-8').split(',')
            data_len = int(data_list[0])
            data_id = int(data_list[1])
            if data_len == len(data) and data_id == FUNC_ID:
                x = int(data_list[2])
                y = int(data_list[3])
                w = int(data_list[4])
                h = int(data_list[5])
                return x, y, w, h
        except:
            return -1, -1, -1, -1
    return -1, -1, -1, -1

while True:
    if ser.in_waiting:
        try:
            data = ser.readline()
            if data:
                # print("Debug Raw:", data) # 调试用
                x, y, w, h = parse_data(data.rstrip(b'\n'))
                if x != -1:
                    print("检测到人脸: x=%d, y=%d, w=%d, h=%d" % (x, y, w, h))
        except Exception as e:
            print("读取错误:", e)
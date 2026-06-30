import os
import sys
import ctypes
import time
import win32gui
import win32process
import win32api
import pyautogui
import keyboard
import threading

# ================== 配置区 ==================
HOTKEY_SCREENSHOT = 'f9'    # 截图快捷键
HOTKEY_EXIT = 'f11'         # 退出快捷键

# 手柄组合键（支持按钮 + 扳机）
# 【按钮索引表】(16个位掩码):
#   0=十字上, 1=十字下, 2=十字左, 3=十字右
#   4=Start, 5=Back, 6=左摇杆按下(LS), 7=右摇杆按下(RS)
#   8=LB, 9=RB, 10(保留), 11(保留)
#   12=A, 13=B, 14=X, 15=Y
#
# 【扳机】LT/RT 为模拟量(0-255)，组合时用特殊标识:
#   -1 = LT (左扳机), -2 = RT (右扳机)
#   触发阈值: 扳机值 > 128 视为按下
#
# 组合键示例:
#   [8, 9]            => LB + RB
#   [-1, -2]          => LT + RT
#   [12, 13]          => A + B
#   [8, -2]           => LB + RT
GAMEPAD_SCREENSHOT_COMBO = [-1, -2]   # 当前组合：LT + RT

# 配置进程名与保存文件夹的映射，小写字母
PROCESS_FOLDER_MAP = {
    "starrail.exe": r"D:\games\Star Rail\Game\StarRail_Data\ScreenShots",
    "yuanshen.exe": r"D:\games\Genshin Impact\Genshin Impact Game\ScreenShot",
    "zenlesszonezero.exe": r"D:\games\ZenlessZoneZero Game\ScreenShot",
    "endfield.exe": r"D:\Pictures\ENDFIELD",
    # 在此添加更多映射...
}
DEFAULT_FOLDER = r"ScreenShot"  # 默认保存目录
# ===========================================

def get_active_process_name():
    """获取当前活动窗口的进程名"""
    hwnd = win32gui.GetForegroundWindow()
    _, pid = win32process.GetWindowThreadProcessId(hwnd)
    handle = win32api.OpenProcess(0x0400, False, pid)  # 获取进程句柄
    try:
        exe_name = win32process.GetModuleFileNameEx(handle, 0)
        return os.path.basename(exe_name).lower()
    finally:
        win32api.CloseHandle(handle)

def save_image(image, path):
    """在后台线程保存图像"""
    try:
        image.save(path, 'PNG')
        print(f"截图已保存: {path}")
    except Exception as e:
        print(f"保存失败: {e} - {path}")

def take_screenshot():
    """截屏并保存到指定目录"""
    # 截屏
    img = pyautogui.screenshot()

    # 生成时间戳文件名
    filename = time.strftime("%Y%m%d%H%M%S") + f"{int(time.time() * 1000) % 1000:03d}.png"
    
    # 获取进程名并确定保存目录
    try:
        process_name = get_active_process_name()
        print(f"当前进程{process_name}")
        folder = PROCESS_FOLDER_MAP.get(process_name, DEFAULT_FOLDER)
    except Exception:
        folder = DEFAULT_FOLDER
    
    # 创建目录（如果不存在）
    os.makedirs(folder, exist_ok=True)
    save_path = os.path.join(folder, filename)
    
    # 保存截图（在后台线程执行）
    threading.Thread(target=save_image, args=(img, save_path)).start()

# ---------- 手柄支持（通过XInput，无需pygame）----------
class XInputGamepad:
    """通过XInput读取手柄状态"""
    TRIGGER_THRESHOLD = 128

    def __init__(self, user_index=0):
        self.user_index = user_index
        self._dll = None
        for dll_name in ("xinput1_4.dll", "xinput1_3.dll"):
            try:
                self._dll = ctypes.windll.LoadLibrary(dll_name)
                break
            except OSError:
                continue
        if not self._dll:
            raise RuntimeError("未找到XInput DLL")
        self._dll.XInputGetState.argtypes = [ctypes.c_uint, ctypes.c_void_p]
        self._dll.XInputGetState.restype = ctypes.c_uint

    def get_state(self):
        """返回(buttons, left_trigger, right_trigger)或None"""
        state = (ctypes.c_uint * 4)()
        result = self._dll.XInputGetState(self.user_index, state)
        if result == 0:
            # state[1] 包含 wButtons(低16位), bLeftTrigger(次高8位), bRightTrigger(最高8位)
            dw = state[1]
            buttons = dw & 0xFFFF
            left_trigger = (dw >> 16) & 0xFF
            right_trigger = (dw >> 24) & 0xFF
            return (buttons, left_trigger, right_trigger)
        return None

    def is_pressed(self, key):
        """
        检查指定按键是否按下
        key: 0-15 为按钮索引，-1 为 LT，-2 为 RT
        """
        state = self.get_state()
        if state is None:
            return False
        buttons, lt, rt = state
        if key == -1:
            return lt > self.TRIGGER_THRESHOLD
        elif key == -2:
            return rt > self.TRIGGER_THRESHOLD
        else:
            return bool(buttons & (1 << key))
# -------------------------------------------------

def gamepad_listener():
    """后台监听手柄组合键并触发截图"""
    try:
        gamepad = XInputGamepad(0)
    except RuntimeError:
        return
    if gamepad.get_state() is None:
        print("未检测到手柄，手柄监听未启动")
        return
    print("手柄已连接，组合键监听中...")

    triggered = False
    while True:
        combo_pressed = all(gamepad.is_pressed(i) for i in GAMEPAD_SCREENSHOT_COMBO)
        if combo_pressed and not triggered:
            print("手柄组合键触发截图")
            take_screenshot()
            triggered = True
        elif not combo_pressed:
            triggered = False
        time.sleep(0.005)

def main():
    print("截屏监听已启动，按 F9 截图...")
    keyboard.add_hotkey(HOTKEY_SCREENSHOT, take_screenshot)

    # 启动手柄监听线程
    threading.Thread(target=gamepad_listener, daemon=True).start()

    keyboard.wait(HOTKEY_EXIT)  # 按f11退出程序
    print("程序已退出")

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if not is_admin():
    # 请求管理员权限重新启动
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
    sys.exit()

if __name__ == "__main__":
    main()
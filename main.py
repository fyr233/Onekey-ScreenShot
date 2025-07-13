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

# 配置进程名与保存文件夹的映射，小写字母
PROCESS_FOLDER_MAP = {
    "starrail.exe": r"D:\games\Star Rail\Game\StarRail_Data\ScreenShots",
    "yuanshen.exe": r"D:\games\Genshin Impact\Genshin Impact Game\ScreenShot",
    "zenlesszonezero.exe": r"D:\games\ZenlessZoneZero Game\ScreenShot",
    # 在此添加更多映射...
}

DEFAULT_FOLDER = r"ScreenShot"  # 默认保存目录

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

def main():
    print("截屏监听已启动，按 F9 截图...")
    keyboard.add_hotkey('f9', take_screenshot)
    keyboard.wait('esc')  # 按ESC退出程序

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
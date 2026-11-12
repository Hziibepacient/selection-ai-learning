# -*- coding: utf-8 -*-
"""
划词直达豆包工作工具（高可靠版 v4）
Ctrl+Q：复制选区 -> 激活豆包工作窗口 -> 点输入区 -> 粘贴 -> 回车发送 -> 切回
Ctrl+Shift+Q 退出
v4：用物理鼠标点击兜底激活（绕过 Windows 前台锁定），加宽输入框识别关键词，日志即时 flush
"""

import keyboard
import pyperclip
import pyautogui
import pygetwindow as gw
import ctypes
import time

# 关闭角落急停，避免坐标异常时整条发送链崩溃
pyautogui.FAILSAFE = False

HOTKEY = 'ctrl+q'
WINDOW_KEYWORD = '豆包工作'

user32 = ctypes.windll.user32
VK_MENU, KEYUP = 0x12, 0x0002


def log(msg):
    print(msg, flush=True)


def fg_title():
    hwnd = user32.GetForegroundWindow()
    buf = ctypes.create_unicode_buffer(256)
    user32.GetWindowTextW(hwnd, buf, 256)
    return buf.value


def get_doubao_work_window():
    for win in gw.getAllWindows():
        if WINDOW_KEYWORD in (win.title or ''):
            return win
    return None


def _fallback_click_input_area(win):
    """物理点击窗口下部中央（输入区大致位置），既聚焦窗口又把光标带进输入区"""
    sw, sh = pyautogui.size()
    cx = int((win.left + win.right) / 2)
    cy = int(win.top + (win.bottom - win.top) * 0.88)
    cx = max(1, min(cx, sw - 2))
    cy = max(1, min(cy, sh - 2))
    log(f'[落点] 兜底点击窗口输入区 ({cx},{cy})')
    pyautogui.click(cx, cy)
    time.sleep(0.25)


def activate_and_click_input():
    """UIA 优先定位输入框；找不到就用窗口矩形兜底点击；成功返回True"""
    try:
        import uiautomation as ua
        root = ua.GetRootControl()
        db = next((w for w in root.GetChildren() if WINDOW_KEYWORD in (w.Name or '')), None)
        if not db:
            return False

        win = get_doubao_work_window()
        if win:
            win.restore()
            db.SetFocus()
            time.sleep(0.15)

        candidates = []

        def walk(c, depth=0):
            if depth > 40:
                return
            n = c.Name or ''
            t = c.ControlTypeName
            if t in ('TextControl', 'EditControl', 'DocumentControl') and any(
                    k in n for k in ('发消息', '使用技能', '添加资料', '输入', '消息', '提问', '说点什么')):
                r = c.BoundingRectangle
                area = (r.right - r.left) * (r.bottom - r.top)
                if area > 0:
                    candidates.append((area, r.top, c))
            try:
                for ch in c.GetChildren():
                    walk(ch, depth + 1)
            except Exception:
                pass

        walk(db)
        candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)

        if candidates:
            placeholder = candidates[0][2]
            r = placeholder.BoundingRectangle
            sw, sh = pyautogui.size()
            if r.right > r.left > 0 and r.bottom > r.top > 0 and r.right <= sw and r.bottom <= sh:
                cx = int((r.left + r.right) / 2)
                cy = int((r.top + r.bottom) / 2)
                pyautogui.click(cx, cy)
                time.sleep(0.25)
                log(f'[落点] UIA命中输入框 ({cx},{cy})')
                return WINDOW_KEYWORD in fg_title()

        # UIA 没命中：物理点击窗口下部输入区
        if win:
            _fallback_click_input_area(win)
        return WINDOW_KEYWORD in fg_title()
    except Exception as e:
        log(f'[warn] UIA激活/点击失败：{e}')
        return False


def force_foreground(win, retries=3):
    """兜底：恢复窗口 + 物理点击，绕前台锁定"""
    for i in range(retries):
        if win:
            user32.ShowWindow(int(win._hWnd), 9)
            _fallback_click_input_area(win)
            time.sleep(0.18)
            if WINDOW_KEYWORD in fg_title():
                log(f'[置前] 点击兜底第{i+1}次成功')
                return True
        time.sleep(0.1)
    return WINDOW_KEYWORD in fg_title()


def on_hotkey():
    log('[触发] 开始执行...')

    for k in ('alt', 'ctrl', 'shift'):
        try:
            keyboard.release(k)
        except Exception:
            pass

    original_window = None
    try:
        original_window = gw.getActiveWindow()
    except Exception:
        pass

    old_clipboard = ''
    try:
        old_clipboard = pyperclip.paste()
    except Exception:
        pass

    # 1. 复制选区
    pyautogui.hotkey('ctrl', 'c')
    time.sleep(0.2)
    selected_text = ''
    try:
        selected_text = pyperclip.paste().strip()
    except Exception:
        pass

    if not selected_text or selected_text == old_clipboard:
        log('[提示] 没有检测到新的选区内容，请先划选文字再按热键')
        return
    log(f'[选区] {len(selected_text)} 字：{selected_text[:50]}')

    # 2. 找窗口
    win = get_doubao_work_window()
    if not win:
        log('[错误] 没找到豆包工作窗口，请确认客户端已打开')
        return

    # 3. 激活并落光标；失败再兜底置前
    ok = activate_and_click_input()
    if not ok:
        log('[置前] UIA未成功，改用点击兜底')
        ok = force_foreground(win)
    if not ok:
        log('[错误] 多次尝试仍未抢到前台，本次未发送')
        return

    # 4. 组消息并粘贴
    message = f'【简历学习】{selected_text}'
    try:
        pyperclip.copy(message)
        time.sleep(0.12)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(0.3)
        # 5. 回车发送
        pyautogui.press('enter')
        log('[完成] 已发送到豆包工作对话')
    except Exception as e:
        log(f'[错误] 粘贴/发送阶段异常：{e}')

    # 6. 切回原窗口
    if original_window:
        time.sleep(0.05)
        try:
            original_window.activate()
        except Exception:
            pass


def main():
    log('=' * 50)
    log('划词直达豆包工作工具已启动（高可靠版 v4）')
    log(f'热键：{HOTKEY.upper()} ｜ 退出：Ctrl+Shift+Q')
    log('=' * 50)
    keyboard.add_hotkey(HOTKEY, on_hotkey)
    keyboard.wait('ctrl+shift+q')
    log('已退出。')


if __name__ == '__main__':
    main()

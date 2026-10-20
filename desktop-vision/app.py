"""Windows desktop shell: WebView2, registered hotkey, single visible frame."""
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
import sys
from pathlib import Path
import threading
import time

ROOT = Path(__file__).resolve().parent
TITLE = 'GWYF · 识牌实验版'
VERSION = '0.3.1'


def app_folder():
    folder = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'GWYF-Vision-Prototype'
    folder.mkdir(parents=True, exist_ok=True)
    return folder


class WindowsCapture:
    def __init__(self):
        if os.name != 'nt':
            raise RuntimeError('全局快捷键和窗口截图需要 Windows 10/11；浏览器可预览和测试图片。')
        self.user = ctypes.WinDLL('user32', use_last_error=True)
        try:
            self.user.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        except (AttributeError, OSError):
            self.user.SetProcessDPIAware()
        self.user.GetForegroundWindow.restype = wintypes.HWND
        self.user.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
        self.user.GetAncestor.restype = wintypes.HWND
        self.user.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        self.user.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
        self.user.IsWindowVisible.argtypes = [wintypes.HWND]
        self.user.IsIconic.argtypes = [wintypes.HWND]
        self.user.GetWindowTextLengthW.argtypes = [wintypes.HWND]
        self.user.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        self.user.IsWindow.argtypes = [wintypes.HWND]
        self._enum_callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        self.user.EnumWindows.argtypes = [self._enum_callback_type, wintypes.LPARAM]
        self.user.EnumWindows.restype = wintypes.BOOL

    def windows(self):
        rows = []
        def visit(hwnd, _):
            if self.user.IsWindowVisible(hwnd):
                n = self.user.GetWindowTextLengthW(hwnd)
                if n:
                    title = ctypes.create_unicode_buffer(n+1)
                    self.user.GetWindowTextW(hwnd, title, n+1)
                    if title.value != TITLE:
                        rows.append({'id': str(hwnd), 'title': title.value,
                                     'minimized': bool(self.user.IsIconic(hwnd))})
            return True
        callback = self._enum_callback_type(visit)
        ctypes.set_last_error(0)
        if not self.user.EnumWindows(callback, 0):
            raise OSError(ctypes.get_last_error(), '无法读取窗口列表，请点击刷新重试。')
        return sorted(rows, key=lambda r: ('gamble' not in r['title'].lower(), r['title']))

    def grab(self, target, overlay=None):
        import mss
        import numpy as np
        hwnd = int(target)
        if not self.user.IsWindow(hwnd) or self.user.IsIconic(hwnd):
            raise ValueError('游戏窗口已关闭或最小化，请恢复后重新选择。')
        foreground = self.user.GetAncestor(self.user.GetForegroundWindow(), 2)
        if foreground != hwnd and not (overlay and foreground == int(overlay)):
            raise ValueError('游戏当前被其他窗口覆盖；请切回游戏后按 Ctrl+Shift+Space。')
        rect, origin = wintypes.RECT(), wintypes.POINT(0, 0)
        if not self.user.GetClientRect(hwnd, ctypes.byref(rect)) or not self.user.ClientToScreen(hwnd, ctypes.byref(origin)):
            raise ValueError('无法取得游戏窗口位置。')
        width, height = rect.right, rect.bottom
        if width < 200 or height < 150:
            raise ValueError('游戏窗口太小。')
        with mss.mss() as sct:
            frame = sct.grab({'left': origin.x, 'top': origin.y, 'width': width, 'height': height})
            return np.asarray(frame)[:, :, :3].copy()


class API:
    def __init__(self):
        self.window = None
        self.native = WindowsCapture() if os.name == 'nt' else None
        self.frame = None
        self.model = None
        self.lock = threading.Lock()
        self.hotkey_status = '等待注册快捷键'
        self.hotkey_manager = None
        self.target = None
        self.exclude_overlay = False

    def status(self):
        return {'version': VERSION, 'bridgeVersion': 2,
                'native': self.native is not None, 'hotkey': self.hotkey_manager.summary() if self.hotkey_manager else self.hotkey_status, 'python': sys.version.split()[0], 'backend': 'OpenCV DNN CPU',
                'modelBytes': sum(p.stat().st_size for p in (ROOT/'models').glob('*.onnx'))}

    def hotkeys(self, request):
        from hotkeys import DEFAULTS
        if not isinstance(request, dict):
            raise ValueError('快捷键设置无效。')
        if self.hotkey_manager:
            return self.hotkey_manager.request(request)
        if request.get('op', 'get') == 'get':
            return {'config': dict(DEFAULTS), 'defaults': dict(DEFAULTS), 'registered': {},
                    'errors': {}, 'paused': False, 'available': False}
        raise ValueError('自定义全局快捷键需要 Windows 桌面版。')

    def _hotkey_active(self):
        try:
            overlay = int(self.window.native.Handle.ToInt64())
            foreground = self.native.user.GetAncestor(self.native.user.GetForegroundWindow(), 2)
            return foreground == overlay or bool(self.target and foreground == int(self.target))
        except Exception:
            return False

    def windows(self):
        return self.native.windows() if self.native else []

    def select_window(self, target):
        if not target:
            self.target = None
            return True
        valid = {r['id'] for r in self.windows()}
        if str(target) not in valid:
            raise ValueError('窗口已失效，请刷新窗口列表。')
        self.target = str(target)
        return True

    def capture(self):
        if not self.native:
            raise ValueError('当前平台请使用“打开测试图片”；快捷截图需在 Windows 运行。')
        if not self.target:
            raise ValueError('请先选择游戏窗口。')
        with self.lock:
            overlay = int(self.window.native.Handle.ToInt64()) if self.window else None
            # Exclude our overlay, or hide only our own window for a single frame.
            # Restore without activation so the game keeps keyboard focus.
            hidden = overlay and not self.exclude_overlay
            self.native.user.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
            foreground = self.native.user.GetAncestor(self.native.user.GetForegroundWindow(), 2)
            if foreground not in (int(self.target), overlay):
                raise ValueError('请先切回游戏窗口再截图。')
            try:
                if hidden:
                    self.native.user.ShowWindow(overlay, 0)
                    time.sleep(.06)
                self.frame = self.native.grab(self.target, overlay)
            finally:
                if hidden:
                    self.native.user.ShowWindow(overlay, 4)
            return self._frame_result()

    def _frame_result(self):
        import cv2
        from recognizer import png_data
        h, w = self.frame.shape[:2]
        preview = self.frame
        if w > 1440:
            preview = cv2.resize(preview, (1440, round(h*1440/w)), interpolation=cv2.INTER_AREA)
        return {'image': png_data(preview), 'width': w, 'height': h,
                'digest': hashlib.sha256(self.frame.tobytes()).hexdigest()}

    def open_image(self):
        import webview
        import cv2
        selection = self.window.create_file_dialog(webview.FileDialog.OPEN, allow_multiple=False,
                    file_types=('图片 (*.png;*.jpg;*.jpeg;*.webp)',))
        if not selection:
            return None
        # imdecode handles Unicode Windows paths.
        import numpy as np
        raw = np.fromfile(selection[0], dtype=np.uint8)
        if raw.size > 35_000_000:
            raise ValueError('测试图片请小于35MB。')
        image = cv2.imdecode(raw, cv2.IMREAD_COLOR)
        if image is None or image.size > 100_000_000:
            raise ValueError('图片无效或分辨率过大。')
        with self.lock:
            self.frame = image
            return self._frame_result()

    def recognize(self, regions, mode):
        if mode not in ('blackjack', 'poker') or set(regions) - {'player', 'dealer'}:
            raise ValueError('识别参数无效。')
        with self.lock:
            if self.frame is None:
                raise ValueError('请先截图。')
            if self.model is None:
                from recognizer import Recognizer
                self.model = Recognizer()
            return self.model.read(self.frame, regions, mode)

    def load_state(self):
        try:
            return json.loads((app_folder()/'state.json').read_text('utf-8'))
        except (OSError, ValueError):
            return None

    def save_state(self, data):
        if not isinstance(data, dict) or len(json.dumps(data)) > 150_000:
            raise ValueError('状态无效。')
        folder = app_folder()
        # Data only: no screenshot, no executable content, no external endpoint.
        temp = folder/'state.tmp'
        temp.write_text(json.dumps(data, ensure_ascii=False), 'utf-8')
        temp.replace(folder/'state.json')
        return True

    def compact(self, enabled):
        if self.window:
            self.window.resize(420 if enabled else 560, 380 if enabled else 820)
        return True


class DesktopBridge:
    """Only expose explicit RPC methods, never Window, WinDLL, locks or models.

    pywebview recursively inspects public attributes. Exposing API.window also
    exposes GUI/native objects and can stall injection before pywebviewready.
    Keeping the controller private prevents that scan and avoids leaking GUI
    methods such as evaluate_js into the page's RPC interface.
    """
    def __init__(self, controller):
        self._controller = controller

    def status(self):
        return self._controller.status()

    def windows(self):
        return self._controller.windows()

    def select_window(self, target):
        return self._controller.select_window(target)

    def capture(self):
        return self._controller.capture()

    def open_image(self):
        return self._controller.open_image()

    def recognize(self, regions, mode):
        return self._controller.recognize(regions, mode)

    def load_state(self):
        return self._controller.load_state()

    def save_state(self, data):
        return self._controller.save_state(data)

    def compact(self, enabled):
        return self._controller.compact(enabled)

    def hotkeys(self, request):
        return self._controller.hotkeys(request)


def main():
    import webview
    api = API()
    if api.native:
        # Reduce screen-capture feedback; supported on Win10 2004+.
        gui = 'edgechromium'
    else:
        gui = None
    api.window = webview.create_window(TITLE, str(ROOT/'web/desktop.html'), js_api=DesktopBridge(api),
                                      width=560, height=820, min_size=(360, 260),
                                      on_top=True, background_color='#10191b', text_select=True)
    if api.native:
        from hotkeys import HotkeyManager

        def dispatch(action):
            name = {'capture': 'captureNow', 'archive': 'archiveCurrent', 'accept': 'acceptDraft', 'reset': 'resetUsedCards'}[action]
            api.window.evaluate_js('window.'+name+' && window.'+name+'()')

        api.hotkey_manager = HotkeyManager(api.native.user, dispatch, app_folder()/'hotkeys.json', api._hotkey_active)

    def loaded():
        if api.native:
            try:
                hwnd = int(api.window.native.Handle.ToInt64())
                api.native.user.SetWindowDisplayAffinity.argtypes = [wintypes.HWND, wintypes.DWORD]
                api.exclude_overlay = bool(api.native.user.SetWindowDisplayAffinity(hwnd, 0x11))
            except Exception:
                pass
        if api.hotkey_manager:
            api.hotkey_manager.start()
        else:
            api.hotkey_status = '当前平台：仅图片测试'

    api.window.events.loaded += loaded
    try:
        webview.start(gui=gui, private_mode=True, http_server=True)
    finally:
        if api.hotkey_manager:
            api.hotkey_manager.close()


if __name__ == '__main__':
    main()

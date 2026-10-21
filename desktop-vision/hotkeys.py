"""Configurable Win32 shortcuts; all registration stays on one message thread."""
from ctypes import wintypes
from pathlib import Path
import ctypes
import json
import os
import queue
import threading
import time

DEFAULTS = {'capture': 'F8', 'archive': 'F9', 'accept': 'F10', 'reset': 'F11', 'discard': 'F7'}
LABELS = {'capture': '识牌', 'archive': '归档', 'accept': '采用', 'reset': '重置', 'discard': '扑克换牌'}
MODIFIERS = {'Ctrl': 2, 'Alt': 1, 'Shift': 4, 'Win': 8}
KEYS = {'Space': 0x20, 'Enter': 0x0D, 'Tab': 9, 'Backspace': 8,
        'Insert': 0x2D, 'Delete': 0x2E, 'Home': 0x24, 'End': 0x23,
        'PageUp': 0x21, 'PageDown': 0x22, 'Up': 0x26, 'Down': 0x28,
        'Left': 0x25, 'Right': 0x27, 'Escape': 0x1B}
KEYS.update({f'F{i}': 0x6F+i for i in range(1, 25)})
KEYS.update({c: ord(c) for c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'})
KEYS.update({f'Num{i}': 0x60+i for i in range(10)})


def parse(binding):
    if binding == '':
        return '', None
    if not isinstance(binding, str) or len(binding) > 60:
        raise ValueError('快捷键格式无效。')
    parts = binding.split('+')
    if not parts or parts[-1] not in KEYS or any(p not in MODIFIERS for p in parts[:-1]):
        raise ValueError('请使用功能键、字母、数字或 Ctrl / Alt / Shift / Win 组合。')
    if len(set(parts)) != len(parts):
        raise ValueError('快捷键包含重复按键。')
    mods = [m for m in MODIFIERS if m in parts[:-1]]
    return '+'.join(mods+[parts[-1]]), (sum(MODIFIERS[m] for m in mods), KEYS[parts[-1]])


def normalise(config):
    legacy = ({'capture', 'archive', 'accept'}, {'capture', 'archive', 'accept', 'reset'})
    if not isinstance(config, dict) or set(config) not in (*legacy, set(DEFAULTS)):
        raise ValueError('需要分别设置识牌、归档、采用、重置和扑克换牌快捷键。')
    result = {action: parse(value)[0] for action, value in config.items()}
    enabled = [value for value in result.values() if value]
    if len(set(enabled)) != len(enabled):
        raise ValueError('不同操作不能使用相同快捷键；不需要的操作可以停用。')
    for action, default in DEFAULTS.items():
        if action not in result:
            # New actions must never overwrite an existing user's binding.
            result[action] = default if default not in enabled else ''
            if result[action]:enabled.append(result[action])
    return {action: result[action] for action in DEFAULTS}


class HotkeyManager:
    def __init__(self, user, callback, path, active=lambda: True):
        self.user, self.callback, self.path, self.active = user, callback, Path(path), active
        self.config = dict(DEFAULTS)
        self.errors = {}
        try:
            raw = json.loads(self.path.read_text('utf-8'))
            self.config = normalise(raw)
            if 'discard' not in raw and not self.config['discard']:
                self.errors['upgrade'] = '原设置已占用 F7；扑克换牌快捷键暂未启用，可在这里另设按键。'
        except FileNotFoundError:
            pass
        except (OSError, ValueError):
            self.errors['settings'] = '快捷键存档无效，已使用默认快捷键。'
        self.registered = {}  # combination -> (native id, action)
        self.next_id = 100
        self.paused_until = 0
        self.context_enabled = False
        self.ready = threading.Event()
        self.stop_event = threading.Event()
        self.wake = threading.Event()
        self.commands = queue.Queue()
        self.thread = None
        self.thread_id = None

    def _snapshot(self):
        return {'config': dict(self.config), 'defaults': dict(DEFAULTS),
                'registered': {a: any(v[1] == a for v in self.registered.values()) for a in DEFAULTS},
                'paused': bool(self.paused_until), 'active': self.context_enabled,
                'errors': dict(self.errors), 'available': True}

    def summary(self):
        return ' · '.join((self.config[a] or '停用')+' '+LABELS[a]
                          + ('（被占用）' if a in self.errors else '') for a in DEFAULTS)

    def _new_registration(self, combo, action):
        self.next_id += 1
        ident = self.next_id
        # MOD_NOREPEAT: a held key must not archive multiple hands.
        if not self.user.RegisterHotKey(None, ident, combo[0] | 0x4000, combo[1]):
            raise ValueError(self.config.get(action, LABELS[action])+' 无法注册，可能被其他程序或系统占用。')
        return ident, action

    def _replace(self, config):
        """Reserve new combinations first. Failure never drops working bindings."""
        wanted = {parse(value)[1]: action for action, value in config.items() if value}
        added = {}
        try:
            for combo, action in wanted.items():
                if combo not in self.registered:
                    added[combo] = self._new_registration(combo, action)
        except Exception as error:
            for ident, _ in added.values():
                self.user.UnregisterHotKey(None, ident)
            value = config[action]
            raise ValueError(value+' 无法注册，可能被其他程序或系统占用；原快捷键保持生效。') from error
        new = {combo: ((self.registered.get(combo) or added[combo])[0], action)
               for combo, action in wanted.items()}
        for combo, (ident, _) in self.registered.items():
            if combo not in wanted:
                self.user.UnregisterHotKey(None, ident)
        self.registered = new

    def _initial_registration(self):
        # One occupied key must not prevent other shortcuts from working.
        for action, value in self.config.items():
            if not value:
                continue
            if parse(value)[1] in self.registered:
                continue
            try:
                self.registered[parse(value)[1]] = self._new_registration(parse(value)[1], action)
                self.errors.pop(action, None)
            except ValueError:
                self.errors[action] = value+' 被占用，请自定义其他快捷键。'

    def _unregister(self):
        for ident, _ in self.registered.values():
            self.user.UnregisterHotKey(None, ident)
        self.registered = {}

    def _handle(self, request):
        if not isinstance(request, dict):
            raise ValueError('快捷键设置无效。')
        op = request.get('op', 'get')
        if op == 'get':
            return self._snapshot()
        if op == 'pause':
            self._unregister()
            self.paused_until = time.monotonic()+60
        elif op == 'resume':
            self.paused_until = 0
            if self.active():self._initial_registration()
        elif op == 'set':
            candidate = normalise(request.get('config'))
            old = dict(self.config)
            previously_active = {a for _, a in self.registered.values()}
            self._replace(candidate)
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                temp = self.path.with_suffix('.tmp')
                temp.write_text(json.dumps(candidate, ensure_ascii=False), 'utf-8')
                temp.replace(self.path)
            except OSError:
                self._replace({a: value if a in previously_active else '' for a, value in old.items()})
                raise ValueError('快捷键未能保存到本机，已恢复原设置。')
            self.config = candidate
            self.paused_until = 0
            self.errors = {}
        else:
            raise ValueError('快捷键操作无效。')
        return self._snapshot()

    def request(self, request):
        if not self.ready.wait(3) or self.stop_event.is_set():
            raise ValueError('快捷键服务尚未就绪，请稍后重试。')
        done = threading.Event()
        result = []
        self.commands.put((request, done, result))
        self.wake.set()
        if not done.wait(5):
            raise ValueError('设置快捷键超时，请重启助手。')
        if isinstance(result[0], Exception):
            raise result[0]
        return result[0]

    def start(self):
        if self.thread:
            return
        self.thread = threading.Thread(target=self._run, daemon=True, name='GWYF hotkeys')
        self.thread.start()

    def _run(self):
        if os.name != 'nt':
            return
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.GetCurrentThreadId.restype = wintypes.DWORD
        self.thread_id = int(kernel.GetCurrentThreadId())
        self.user.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
        self.user.RegisterHotKey.restype = wintypes.BOOL
        self.user.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
        self.user.PeekMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND,
                                           wintypes.UINT, wintypes.UINT, wintypes.UINT]
        message = wintypes.MSG()
        self.user.PeekMessageW(ctypes.byref(message), None, 0, 0, 0)
        self.context_enabled = bool(self.active())
        if self.context_enabled:self._initial_registration()
        self.ready.set()
        try:
            while not self.stop_event.is_set():
                self.wake.clear()
                while not self.commands.empty():
                    request, done, result = self.commands.get_nowait()
                    try:
                        result.append(self._handle(request))
                    except Exception as error:
                        result.append(error)
                    finally:
                        done.set()
                if self.paused_until and time.monotonic() >= self.paused_until:
                    self.paused_until = 0
                    if self.active():self._initial_registration()
                active = bool(self.active())
                if not self.paused_until and active and not self.context_enabled:
                    self._initial_registration()
                if not active and self.registered:
                    self._unregister()
                self.context_enabled = active
                while self.user.PeekMessageW(ctypes.byref(message), None, 0, 0, 1):
                    if message.message == 0x0312 and not self.paused_until and active:
                        action = next((a for ident, a in self.registered.values()
                                       if ident == message.wParam), None)
                        if action:
                            try:
                                self.callback(action)
                            except Exception:
                                pass
                self.wake.wait(.025)
        finally:
            self._unregister()

    def close(self):
        self.stop_event.set()
        self.wake.set()
        if self.thread:
            self.thread.join(2)

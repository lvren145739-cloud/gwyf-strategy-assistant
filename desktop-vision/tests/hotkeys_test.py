"""Registration rollback, swaps, persistence and recording suspension."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from hotkeys import HotkeyManager,DEFAULTS,parse,normalise

class NativeFixture:
    def __init__(self):self.bindings={};self.occupied=set()
    def RegisterHotKey(self,window,ident,mods,key):
        combo=(mods&15,key)
        if combo in self.occupied or combo in self.bindings.values():return False
        self.bindings[ident]=combo;return True
    def UnregisterHotKey(self,window,ident):return self.bindings.pop(ident,None) is not None

class HotkeyTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'hotkeys.json';self.native=NativeFixture()
        self.manager=HotkeyManager(self.native,lambda action:None,self.path)
        self.manager._initial_registration()
    def test_normalisation_and_duplicate_validation(self):
        self.assertEqual(parse('Shift+Ctrl+A'),('Ctrl+Shift+A',(6,65)))
        for config in [dict(capture='F8',archive='F8',accept='F10'),dict(capture='Ctrl+Ctrl+A',archive='F9',accept='F10'),dict(capture='__import__',archive='F9',accept='F10')]:
            with self.assertRaises(ValueError):normalise(config)
    def test_conflict_preserves_every_working_key(self):
        before=dict(self.native.bindings);self.native.occupied.add(parse('Ctrl+F11')[1])
        with self.assertRaisesRegex(ValueError,'原快捷键保持生效'):
            self.manager._handle({'op':'set','config':dict(capture='F7',archive='Ctrl+F11',accept='F10')})
        self.assertEqual(self.native.bindings,before);self.assertEqual(self.manager.config,DEFAULTS)
        self.assertFalse(self.path.exists())
    def test_swap_reuses_native_combinations_and_persists(self):
        before=set(self.native.bindings);config={**DEFAULTS,'capture':'F9','archive':'F8'}
        self.manager._handle({'op':'set','config':config})
        self.assertEqual(set(self.native.bindings),before)
        self.assertEqual(self.manager.registered[parse('F8')[1]][1],'archive')
        self.assertEqual(HotkeyManager(self.native,print,self.path).config,config)
    def test_record_pause_resume_and_repeated_resume(self):
        self.manager._handle({'op':'pause'});self.assertFalse(self.native.bindings)
        self.assertTrue(self.manager._snapshot()['paused'])
        self.manager._handle({'op':'resume'});before=dict(self.native.bindings)
        self.manager._handle({'op':'resume'});self.assertEqual(self.native.bindings,before)
    def test_write_error_rolls_back_and_never_changes_hand_state(self):
        state=self.path.with_name('state.json');state.write_text('{"untouched":true}')
        before=dict(self.manager.config)
        with patch.object(Path,'replace',side_effect=PermissionError('fixture')):
            with self.assertRaisesRegex(ValueError,'恢复原设置'):
                self.manager._handle({'op':'set','config':dict(capture='F7',archive='F9',accept='F10')})
        self.assertEqual(self.manager.config,before)
        self.assertEqual(set(self.native.bindings.values()),{parse(v)[1] for v in before.values()})
        self.assertEqual(state.read_text(),'{"untouched":true}')
    def test_one_occupied_key_does_not_disable_others(self):
        self.manager._unregister();self.native.occupied.add(parse('F8')[1])
        self.manager._initial_registration()
        self.assertIn('capture',self.manager.errors)
        self.assertEqual({a for _,a in self.manager.registered.values()},{'archive','accept','reset'})
    def test_disable_and_bad_saved_config(self):
        self.manager._handle({'op':'set','config':dict(capture='',archive='F9',accept='F10')})
        self.assertFalse(self.manager._snapshot()['registered']['capture'])
        self.path.write_text('{"untrusted":"wrong"}')
        loaded=HotkeyManager(self.native,print,self.path)
        self.assertEqual(loaded.config,DEFAULTS);self.assertIn('settings',loaded.errors)

if __name__=='__main__':unittest.main()

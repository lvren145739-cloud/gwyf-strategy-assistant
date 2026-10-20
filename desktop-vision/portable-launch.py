"""Bundled Python entrypoint. Logs startup errors and reports them in Windows UI."""
from pathlib import Path
import ctypes,json,logging,os,subprocess,sys,traceback
ROOT=Path(__file__).resolve().parent

def webview2_installed():
 import winreg
 # Evergreen runtime client GUID. Check per-user, machine and WOW64 views.
 client='{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}'
 for hive in (winreg.HKEY_CURRENT_USER,winreg.HKEY_LOCAL_MACHINE):
  for view in (winreg.KEY_WOW64_32KEY,winreg.KEY_WOW64_64KEY):
   try:
    with winreg.OpenKey(hive,r'Software\Microsoft\EdgeUpdate\Clients'+'\\'+client,0,winreg.KEY_READ|view) as key:
     value=winreg.QueryValueEx(key,'pv')[0]
     if value and value!='0.0.0.0':return True
   except OSError:pass
 return False

def main():
 if os.name!='nt':raise RuntimeError('The portable launcher is for Windows 10/11 x64.')
 # Keep all session logs out of Program Files / the extracted read-only bundle.
 folder=Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'GWYF-Vision-Prototype'
 folder.mkdir(parents=True,exist_ok=True);log_path=folder/'startup.log'
 logging.basicConfig(filename=log_path,level=logging.INFO,encoding='utf-8',format='%(asctime)s %(levelname)s %(message)s')
 try:
  logging.info('Starting GWYF Vision 0.3.1; Python %s',sys.version.split()[0])
  if not webview2_installed():
   installer=ROOT/'runtime-support/MicrosoftEdgeWebView2RuntimeInstallerX64.exe'
   if not installer.is_file():raise RuntimeError('缺少WebView2运行时与随包安装器，请重新完整解压。')
   # Verify the packaged executable before allowing it to run. The only external
   # setup is Microsoft's per-user Evergreen installer, never arbitrary scripts.
   import hashlib
   expected=json.loads((ROOT/'runtime-support/webview2-offline-source.json').read_text('utf-8'))['sha256']
   if hashlib.sha256(installer.read_bytes()).hexdigest()!=expected:raise RuntimeError('WebView2安装器校验失败，请重新下载完整包。')
   print('Preparing Microsoft WebView2 for this Windows user. Please wait...',flush=True)
   result=subprocess.run([str(installer),'/silent','/install'],cwd=str(ROOT),timeout=240,capture_output=True)
   logging.info('WebView2 setup exit code: %s',result.returncode)
   if not webview2_installed():raise RuntimeError('WebView2未能安装完成。请重试启动，或手动运行 runtime-support 中的微软安装器。')
  # The distribution is self-contained: no pip install, no system Python change.
  import app
  app.main()
 except Exception:
  logging.exception('Startup failed')
  ctypes.windll.user32.MessageBoxW(None,'启动没有完成。具体错误已写入：\n'+str(log_path)+'\n\n'+traceback.format_exc(limit=2)[-1500:],'GWYF · 启动错误',0x10)
  raise

if __name__=='__main__':main()

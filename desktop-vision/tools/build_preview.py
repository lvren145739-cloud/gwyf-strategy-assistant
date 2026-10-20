"""Make a standalone manual-input UI preview; native inference is in app.py."""
from pathlib import Path
root=Path(__file__).resolve().parents[1];web=root/'web'
html=(web/'index.html').read_text('utf-8')
(web/'desktop.html').write_text(html.replace('<head>', '<head><meta name="gwyf-desktop" content="1">'),'utf-8')
html=html.replace('<link rel="stylesheet" href="style.css">','<style>'+(web/'style.css').read_text('utf-8')+'</style>')
worker=(web/'engine.js').read_text('utf-8')+'\n'+(web/'blackjack-engine.js').read_text('utf-8')+'\n'+(web/'solver-worker.js').read_text('utf-8').replace("importScripts('engine.js','blackjack-engine.js');",'')
scripts=''
for name in ['engine.js','state.js','recognition-policy.js','ui.js']:
    code=(web/name).read_text('utf-8')
    if name=='ui.js':
        import json
        code='const GWYF_WORKER_URL=URL.createObjectURL(new Blob(['+json.dumps(worker,ensure_ascii=False)+'],{type:"application/javascript"}));\n'+code
        code=code.replace("new Worker('solver-worker.js')",'new Worker(GWYF_WORKER_URL)')
    scripts+='<script>'+code.replace('</script','<\\/script')+'</script>\n'
start=html.index('<script src="engine.js">');end=html.index('</body>')
html=html[:start]+scripts+html[end:]
(root/'界面预览-无需安装.html').write_text(html,'utf-8')
print('Built standalone UI preview (manual input only).')

from playwright.sync_api import sync_playwright
from pathlib import Path
import shutil
root=Path(__file__).resolve().parents[1]
preview_test=root/'web/preview-test.html'
shutil.copyfile(root/'界面预览-无需安装.html',preview_test)
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
 page=b.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto('http://127.0.0.1:8767/preview-test.html');page.locator('#manual summary').click()
 for r in ['10','6']:page.locator('[data-rank="'+r+'"]').click()
 page.locator('#role').select_option('dealer');page.locator('[data-rank="10"]').click();page.locator('#apply').click()
 page.wait_for_function("document.querySelector('#advice h1').textContent.includes('HIT')",timeout=10000)
 assert not errors,errors;print('Standalone HTML and embedded decision worker passed over local HTTP; file navigation is blocked by this cloud Chromium policy.');b.close()

preview_test.unlink(missing_ok=True)

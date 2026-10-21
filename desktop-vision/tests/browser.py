from playwright.sync_api import sync_playwright
from pathlib import Path
import json
root=Path(__file__).resolve().parents[1]
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
 page=b.new_page(viewport={'width':560,'height':820});errors=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto('http://127.0.0.1:8770/');page.wait_for_timeout(300)
 page.locator('#manual summary').click()
 for r in ['10','6']:page.locator('[data-rank="'+r+'"]').click()
 page.locator('#role').select_option('dealer');page.locator('[data-rank="10"]').click()
 page.locator('#apply').click();page.wait_for_function("document.querySelector('#advice h1').textContent.includes('HIT')",timeout=15000)
 page.screenshot(path=str(root/'tests/preview-blackjack.png'),full_page=True)
 page.locator('#archive').click();assert page.locator('#usedCount').inner_text()=='3 张'
 page.locator('#undo').click();assert page.locator('#usedCount').inner_text()=='0 张'
 page.locator('[data-mode=poker]').click();page.locator('#clearDraft').click()
 page.locator('#suit').select_option('spades')
 for r in ['10','J','Q','K','A']:page.locator('[data-rank="'+r+'"]').click()
 page.locator('#apply').click();page.wait_for_function("document.querySelector('#advice h1').textContent.includes('保留全部')",timeout=20000)
 assert page.locator('#advice h1').inner_text()=='保留全部五张'
 page.locator('#compact').click();page.screenshot(path=str(root/'tests/preview-compact.png'))
 for width in [360,420,560]:
  page.set_viewport_size({'width':width,'height':820});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
 print(json.dumps({'errors':errors,'blackjack':'16 vs10 HIT','history':'archive and undo','poker':'royal flush hold all','responsive':[360,420,560]},ensure_ascii=False))
 assert not errors
 b.close()

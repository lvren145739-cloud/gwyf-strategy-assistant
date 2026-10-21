from playwright.sync_api import sync_playwright
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox']);page=b.new_page(viewport={'width':420,'height':341});page.goto('http://127.0.0.1:8770/');page.evaluate("() => {state=VisionState.blank();state=VisionState.commit(state,[{rank:'10',role:'player'},{rank:'6',role:'player'},{rank:'10',role:'dealer'}]);render();calculate();}");page.wait_for_function("document.querySelector('#advice h1').textContent.includes('HIT')");page.locator('#compact').click()
 assert page.locator('#status').bounding_box()['y']+page.locator('#status').bounding_box()['height'] <= 341
 assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
 print(page.evaluate("JSON.stringify(['header','#advice','#current','.actions','#status'].map(s=>{const r=document.querySelector(s).getBoundingClientRect();return [s,r.top,r.bottom]}))"));page.screenshot(path='/workspace/vision-v3/tests/compact-actual.png');b.close()

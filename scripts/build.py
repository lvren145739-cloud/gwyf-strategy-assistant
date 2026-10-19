from pathlib import Path
import sys, json
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
parts = ['views-main.js', 'views-tables.js', 'views-slots.js', 'views-risk.js', 'views-blackjack.js', 'views-poker.js', 'views-extra.js']
app = (SRC / 'app.js').read_text().replace('/*__VIEWS__*/', '\n'.join((SRC / p).read_text() for p in parts)).replace('/*__EVENTS__*/', (SRC / 'events.js').read_text()).replace('/*__LICENSE__*/', json.dumps((ROOT / 'LICENSE').read_text(), ensure_ascii=False))
js = '\n'.join((SRC / p).read_text() for p in ['engine.js', 'blackjack-engine.js', 'data.js']) + '\n' + app
assert '</script' not in js.lower()
html = (SRC / 'shell.html').read_text().replace('/*__CSS__*/', (SRC / 'style.css').read_text()).replace('/*__JS__*/', js).encode()
for name in ['index.html', 'GWYF_策略决策器.html']:
    path = ROOT / name
    if '--check' in sys.argv:
        assert path.read_bytes() == html, f'{name} differs from source build'
    else:
        path.write_bytes(html)
print(f'Build {"verified" if "--check" in sys.argv else "complete"}: {len(html):,} bytes; both entry files identical')

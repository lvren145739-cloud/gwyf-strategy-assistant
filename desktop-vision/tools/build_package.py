from pathlib import Path
import hashlib,zipfile
root=Path(__file__).resolve().parents[1]
for p in root.glob('*.bat'):
    content=p.read_text('utf-8').replace('\r\n','\n')
    p.write_bytes(content.replace('\n','\r\n').encode('utf-8'))
files=[]
for p in sorted(root.rglob('*')):
    if not p.is_file():continue
    rel=p.relative_to(root)
    if any(part in {'research','runtime','__pycache__'} or part.startswith('.venv') for part in rel.parts):continue
    if p.name in {'SHA256SUMS.txt','preview-test.html'} or p.suffix in {'.pyc','.zip','.log'}:continue
    if rel.parts[0]=='tests' and p.suffix=='.png' and p.name not in {'compact-actual.png','preview-draft.png'}:continue
    files.append(p)
manifest=''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(root).as_posix()+'\n' for p in files)
(root/'SHA256SUMS.txt').write_text(manifest,'utf-8');files.append(root/'SHA256SUMS.txt')
output=root.parent/'GWYF-Vision-0.3.0.zip'
with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for p in files:z.write(p,'GWYF-Vision-0.3.0/'+p.relative_to(root).as_posix())
with zipfile.ZipFile(output) as z:
    assert z.testzip() is None
    for line in manifest.splitlines():
        digest,path=line.split('  ',1)
        assert hashlib.sha256(z.read('GWYF-Vision-0.3.0/'+path)).hexdigest()==digest
print(output.name,output.stat().st_size,hashlib.sha256(output.read_bytes()).hexdigest(),len(files),'files')

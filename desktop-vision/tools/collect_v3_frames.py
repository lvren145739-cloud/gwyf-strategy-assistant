"""Research-only extraction; raw third-party frames are not distributed."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import json,os,subprocess
from PIL import Image,ImageDraw
r=Path('/workspace/vision-prototype/research');out=r/'v3-frames';out.mkdir(exist_ok=True)
archive='https://archive.org/download/pc-longplay-gamble-with-your-friends/PC_Longplay_Gamble_With_Your_Friends.mp4'
b=json.loads((r/'v3-bili.json').read_text());f=next(f for f in b['formats'] if f['format_id']=='30080');headers=''.join(f'{k}: {v}\r\n' for k,v in f.get('http_headers',b.get('http_headers',{})).items())
jobs=[('long',t,archive,None) for t in [240,248,1428,1440,1450,2020,2035,2050,2075,2082,2150,2250,2400,2600]]+ [('bili',t,f['url'],headers) for t in [60,120,180,240,300,360,420,460,540,570,590,610,630,660,700,740,800,860,920]]
def run(job):
 name,t,url,head=job;p=out/f'{name}-{t}.jpg'
 if p.exists():return p.name,'cached'
 args=['ffmpeg','-hide_banner','-loglevel','error','-http_proxy',os.environ.get('HTTPS_PROXY','http://proxy:8080')]
 if head:args+=['-headers',head]
 args+=['-ss',str(t),'-i',url,'-frames:v','1','-q:v','2','-update','1','-threads','1','-y',str(p)]
 try:
  result=subprocess.run(args,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=55)
  return p.name,'ok' if result.returncode==0 else result.stderr.decode(errors='replace')[-140:]
 except subprocess.TimeoutExpired:return p.name,'timeout'
with ThreadPoolExecutor(max_workers=3) as pool:
 for result in pool.map(run,jobs):print(result,flush=True)
files=sorted(out.glob('*.jpg'));sheet=Image.new('RGB',(1440,((len(files)+4)//5)*185),'#222');d=ImageDraw.Draw(sheet)
for i,p in enumerate(files):
 im=Image.open(p);im.thumbnail((288,162));x=i%5*288;y=i//5*185;sheet.paste(im,(x,y));d.text((x,y+162),p.stem,fill='white')
sheet.save(r/'v3-new-contact.jpg');print(len(files),'frames',flush=True)

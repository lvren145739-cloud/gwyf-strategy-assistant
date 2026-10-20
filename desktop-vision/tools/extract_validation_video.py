import json,os,subprocess
from pathlib import Path
from PIL import Image,ImageDraw
root=Path(__file__).resolve().parents[1];r=root/'research';x=json.loads((r/'v2-video.json').read_text());f=next(f for f in x['formats'] if f['format_id']=='30080');headers=''.join(f'{k}: {v}\r\n' for k,v in f.get('http_headers',x.get('http_headers',{})).items());out=r/'v2-unseen';out.mkdir(exist_ok=True)
subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-http_proxy',os.environ.get('HTTPS_PROXY','http://proxy:8080'),'-headers',headers,'-i',f['url'],'-vf','fps=1/4','-q:v','2','-threads','1','-y',str(out/'%03d.jpg')],check=True,timeout=120)
files=sorted(out.glob('*.jpg'));sheet=Image.new('RGB',(1280,((len(files)+3)//4)*200),'#222');d=ImageDraw.Draw(sheet)
for i,p in enumerate(files):
 im=Image.open(p);im.thumbnail((320,180));a=i%4*320;b=i//4*200;sheet.paste(im,(a,b));d.text((a,b+180),p.stem,fill='white')
sheet.save(r/'v2-unseen-contact.jpg');print(len(files),'frames')

import subprocess,json
from pathlib import Path
root=Path(__file__).resolve().parents[1];results=[]
for n in range(11,16):
 executable=root.parent/('vision-py3'+str(n))/'bin/python'
 p=subprocess.run([str(executable),str(root/'tests/runtime_smoke.py')],capture_output=True,text=True,check=True);results.append(json.loads(p.stdout));print(results[-1]['python'],'passed',flush=True)
report={'scope':'Real standard CPython Linux x64 inference/import/JSON/Unicode-path checks. Windows dependency locks separately resolved for 3.11-3.15; Windows native GUI/capture not executed. Free-threaded builds not supported.','runtimes':results,'sameOutput':len({x['recognitionDigest'] for x in results})==1,'windowsDependencyLocks':[p.name for p in (root/'tests/windows-locks').glob('*.txt')]}
assert report['sameOutput'];(root/'tests/python-compatibility.json').write_text(json.dumps(report,indent=2))

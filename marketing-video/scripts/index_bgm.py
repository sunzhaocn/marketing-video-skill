"""Probe and fully decode local BGM files; keep a portable music index."""
import argparse,concurrent.futures,hashlib,json,subprocess
from pathlib import Path

def check(root,p):
 row={'path':p.relative_to(root).as_posix(),'category':p.relative_to(root/'assets/BGM').parts[0],'file':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
 try:
  meta=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(p)]))
  a=next(x for x in meta['streams'] if x['codec_type']=='audio')
  row.update(duration=float(meta['format']['duration']),codec=a['codec_name'],sample_rate=int(a['sample_rate']),channels=a['channels'])
  res=subprocess.run(['ffmpeg','-v','error','-i',str(p),'-map','0:a:0','-f','null','-'],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=180)
  row['decodable']=res.returncode==0 and not res.stderr
  if not row['decodable']:row['error']=res.stderr.decode(errors='replace')[:1000]
 except Exception as e:row.update(decodable=False,error=str(e))
 return row

def build(root):
 root=Path(root).resolve();folder=root/'assets/BGM'
 previous=root/'assets/bgm-index.json'
 prior={x['path']:x for x in json.loads(previous.read_text(encoding='utf-8')).get('tracks',[])} if previous.exists() else {}
 files=sorted(p for p in folder.rglob('*') if p.is_file() and p.suffix.lower() in {'.mp3','.flac','.wav','.m4a','.aac','.ogg','.opus'}) if folder.exists() else []
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:rows=list(ex.map(lambda p:check(root,p),files))
 for i,row in enumerate(rows):
  row['id']=f'B{i+1:03}'
  for k in ['title','artists','requested','match_kind','source','source_note']:
   if k in prior.get(row['path'],{}):row[k]=prior[row['path']][k]
 data={'total':len(rows),'decodable':sum(x['decodable'] for x in rows),'bytes':sum(x['bytes'] for x in rows),'tracks':rows,'distribution':'Audio files are local-only; public repository provides index and guidance.'}
 previous.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({k:v for k,v in data.items() if k!='tracks'},ensure_ascii=False),flush=True)
 return data
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--skill-root',default=str(Path(__file__).resolve().parents[1]));args=parser.parse_args();build(args.skill_root)

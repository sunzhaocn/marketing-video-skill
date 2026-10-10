"""Index actual image formats/animation and create numbered contact sheets."""
import argparse,hashlib,json,math
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageOps

def build(root):
 root=Path(root).resolve();assets=root/'assets';previews=assets/'previews';previews.mkdir(parents=True,exist_ok=True)
 font_paths=['C:/Windows/Fonts/msyh.ttc','/System/Library/Fonts/PingFang.ttc','/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc']
 font_path=next((p for p in font_paths if Path(p).exists()),None)
 if font_path is None:raise RuntimeError('需要安装中文字体：微软雅黑、苹方或 Noto Sans CJK。')
 font=ImageFont.truetype(font_path,16)
 rows=[];tiles=[]
 for group,folder in [('emoji','表情包'),('background','背景素材')]:
  files=sorted(p for p in (assets/folder).rglob('*') if p.is_file()) if (assets/folder).exists() else []
  for p in files:
   row={'id':len(rows)+1,'group':group,'path':p.relative_to(root).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
   tile=Image.new('RGB',(180,190),'#edf0ec');d=ImageDraw.Draw(tile)
   try:
    with Image.open(p) as im:
     count=getattr(im,'n_frames',1);fmt=im.format;size=im.size;total=0
     if count>1:
      for k in range(count):im.seek(k);total+=im.info.get('duration',0)
     im.seek(0);thumb=im.convert('RGBA');thumb.thumbnail((164,140))
     tile.paste(thumb,((180-thumb.width)//2,(145-thumb.height)//2),thumb)
     row.update(format=fmt,width=size[0],height=size[1],frames=count,animated=count>1,duration_ms=total,readable=True)
     d.text((8,146),f"{row['id']:03} {fmt} {'动态' if count>1 else '静态'}",font=font,fill='#173b29')
     d.text((8,168),p.stem[:15],font=font,fill='#173b29')
   except Exception as e:
    row.update(readable=False,error=str(e));d.text((8,70),f"{row['id']:03} 无法解析",font=font,fill='red')
   rows.append(row);tiles.append(tile)
 sheets=[]
 for start in range(0,len(tiles),50):
  page=Image.new('RGB',(900,1900),'white')
  for offset,tile in enumerate(tiles[start:start+50]):page.paste(tile,((offset%5)*180,(offset//5)*190))
  p=previews/f'catalog-{start//50+1:02}.jpg';page.save(p,quality=85);sheets.append(p.relative_to(root).as_posix())
 result={'assets':rows,'contact_sheets':sheets,'total':len(rows),'readable':sum(r['readable'] for r in rows),'animated':sum(r.get('animated',False) for r in rows)}
 (assets/'library-index.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({k:v for k,v in result.items() if k!='assets'},ensure_ascii=False))
 return result
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--skill-root',default=str(Path(__file__).resolve().parents[1]));args=parser.parse_args();build(args.skill_root)

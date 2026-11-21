"""Derive byte-identical final downloads from the complete project archive."""
import argparse,copy,hashlib,json,pathlib,shutil,zipfile
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def derive(records,source,output,verify=True):
 output.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(source) as z:
  for r in records:
   if r.get('transport')!='derived':continue
   target=output/r['name'];kind=r['kind']
   if kind=='catalog':
    members=[i for i in z.infolist() if i.filename.startswith('06_delivery/') and i.filename.endswith('.xlsx') and '/' not in i.filename[12:]];assert len(members)==1
    with z.open(members[0]) as a,target.open('wb') as b:shutil.copyfileobj(a,b,1048576)
   else:
    prefix='04_assets/' if kind=='all_images' else '06_delivery/' if kind=='review' else None;assert prefix
    members=[i for i in z.infolist() if i.filename.startswith(prefix) and not i.is_dir() and (kind!='all_images' or (i.filename.endswith('.png') and i.filename.split('/')[1] in ['characters','scenes','props','vfx']))]
    if kind=='all_images':assert len(members)==392
    with zipfile.ZipFile(target,'w',zipfile.ZIP_STORED,allowZip64=True) as dest:
     for old in members:
      info=copy.copy(old);info.filename=old.filename[len(prefix):];info.orig_filename=info.filename
      with z.open(old) as a,dest.open(info,'w') as b:shutil.copyfileobj(a,b,1048576)
   with zipfile.ZipFile(target) as child:
    assert child.testzip() is None
    if kind=='catalog':assert len([n for n in child.namelist() if n.startswith('xl/media/')])==392
   if verify:assert target.stat().st_size==r['bytes'] and sha(target)==r['sha256'],r['name']
   else:r.update(bytes=target.stat().st_size,sha256=sha(target))
   print('DERIVED PASS',r['name'],target.stat().st_size,flush=True)
 return records
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--manifest',type=pathlib.Path,required=True);p.add_argument('--archive-dir',type=pathlib.Path,required=True);p.add_argument('--output-dir',type=pathlib.Path,required=True);a=p.parse_args();rr=json.loads(a.manifest.read_text());full=next(r for r in rr if r['kind']=='full_project');source=a.archive_dir/full['name'];assert source.stat().st_size==full['bytes'] and sha(source)==full['sha256'];derive(rr,source,a.output_dir)

"""Derive byte-identical downloads from an already verified complete project ZIP."""
import argparse,copy,hashlib,json,pathlib,shutil,zipfile
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for block in iter(lambda:f.read(1048576),b''):h.update(block)
 return h.hexdigest()
def derive(manifest,archive_dir,output_dir):
 records=json.loads(manifest.read_text());assert len(records)==4
 for r in records:assert pathlib.Path(r['name']).name==r['name']
 full=next(r for r in records if r['kind']=='full_project');source=archive_dir/full['name'];assert source.stat().st_size==full['bytes'] and sha(source)==full['sha256']
 output_dir.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(source) as project:
  for r in records:
   if r.get('transport')!='derived':continue
   target=output_dir/r['name'];kind=r['kind']
   if kind=='catalog':
    members=[x for x in project.infolist() if x.filename.startswith('06_delivery/') and '/' not in x.filename[len('06_delivery/'):] and x.filename.endswith('.xlsx')];assert len(members)==1
    with project.open(members[0]) as src,target.open('wb') as dest:shutil.copyfileobj(src,dest,1048576)
   else:
    prefix='04_assets/scenes/' if kind=='scenes_only' else '06_delivery/' if kind=='review' else None;assert prefix
    members=[x for x in project.infolist() if x.filename.startswith(prefix) and not x.is_dir() and (kind!='scenes_only' or '/' not in x.filename[len(prefix):])]
    if kind=='scenes_only':assert len(members)==304 and all(x.filename.endswith('.png') for x in members)
    with zipfile.ZipFile(target,'w',zipfile.ZIP_STORED,allowZip64=True) as child:
     for original in members:
      info=copy.copy(original);info.filename=original.filename[len(prefix):];info.orig_filename=info.filename
      with project.open(original) as src,child.open(info,'w') as dest:shutil.copyfileobj(src,dest,1048576)
   assert target.stat().st_size==r['bytes'] and sha(target)==r['sha256'],('Derived file differs',r['name'])
   with zipfile.ZipFile(target) as child:
    assert child.testzip() is None
    if kind=='catalog':assert len([n for n in child.namelist() if n.startswith('xl/media/')])==566
   print('DERIVED PASS',r['name'],r['bytes'],r['sha256'],flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--manifest',type=pathlib.Path,required=True);p.add_argument('--archive-dir',type=pathlib.Path,required=True);p.add_argument('--output-dir',type=pathlib.Path,required=True);a=p.parse_args();derive(a.manifest,a.archive_dir,a.output_dir)

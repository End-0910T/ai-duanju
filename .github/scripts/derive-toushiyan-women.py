"""Apply the checked replacement assets to the original release archive."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

def sha(p):
    digest=hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):digest.update(block)
    return digest.hexdigest()

def copy_member(src, info, target, name=None):
    new=copy.copy(info)
    if name is not None:new.filename=new.orig_filename=name
    with src.open(info) as a,target.open(new,'w') as b:shutil.copyfileobj(a,b,1048576)

def derive(base,overlay,out,records,verify=True):
    out.mkdir(exist_ok=True,parents=True)
    paths={r['kind']:out/r['name'] for r in records}
    assert set(paths)=={'full_project','women_png','catalog'}
    with zipfile.ZipFile(base) as original,zipfile.ZipFile(overlay) as additions:
        meta=json.loads(additions.read('overlay.json'))
        assert base.stat().st_size==meta['base_bytes'] and sha(base)==meta['base_sha256']
        revised=meta['replacements']
        orig={i.filename:i for i in original.infolist()}
        add={i.filename:i for i in additions.infolist() if i.filename!='overlay.json'}
        assert len(revised)==len(set(revised.values()))==38
        assert set(revised)<=orig.keys() and set(revised.values())<=add.keys()
        assert not set(revised)&add.keys()
        original_index={m['id']:m for m in json.loads(original.read('02_tables/delivery-index.json'))}
        new_index={m['id']:m for m in json.loads(additions.read('02_tables/delivery-index.json'))}
        assert len(original_index)==len(new_index)==367 and set(original_index)==set(new_index)
        for k,a in new_index.items():
            p=original_index[k]
            if p['output_path'] in revised:
                name=revised[p['output_path']]
                assert a['output_path']==name and hashlib.sha256(additions.read(name)).hexdigest()==a['sha256']
            else:
                assert a['sha256']==p['sha256'] and a['output_path']==p['output_path']
        with zipfile.ZipFile(paths['full_project'],'w',compression=zipfile.ZIP_STORED) as final:
            for name,i in orig.items():
                if name in revised:continue
                if name in add:copy_member(additions,add[name],final)
                else:copy_member(original,i,final)
            for name,i in add.items():
                if name not in orig:copy_member(additions,i,final)
        with zipfile.ZipFile(paths['women_png'],'w',compression=zipfile.ZIP_STORED) as final:
            for name in sorted(revised.values()):
                assert name.startswith('04_assets/characters/') and name.endswith('.png')
                copy_member(additions,add[name],final,Path(name).name)
        xls=[i for n,i in add.items() if n.startswith('06_delivery/') and n.endswith('.xlsx')]
        assert len(xls)==1
        with additions.open(xls[0]) as a,paths['catalog'].open('wb') as b:shutil.copyfileobj(a,b)
    for r in records:
        p=paths[r['kind']]
        with zipfile.ZipFile(p) as result:
            assert result.testzip() is None
            if r['kind']=='full_project':
                pngs={n for n in result.namelist() if n.startswith('04_assets/') and n.endswith('.png')}
                assert pngs=={a['output_path'] for a in new_index.values()}
                assert len(pngs)==367
            elif r['kind']=='women_png':
                assert len(result.namelist())==38 and all(n.endswith('.png') for n in result.namelist())
            else:
                assert len([n for n in result.namelist() if n.startswith('xl/media/')])==367
        info=dict(bytes=p.stat().st_size,sha256=sha(p))
        if verify:assert all(info[k]==r[k] for k in info),r['name']
        else:r.update(info)
        assert p.stat().st_size<2*1024**3
        print('PACKAGE VERIFIED',r['name'],p.stat().st_size,flush=True)
    return records

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for s in ['base','overlay','manifest','out']:p.add_argument('--'+s,required=True,type=Path)
    a=p.parse_args()
    derive(a.base,a.overlay,a.out,json.loads(a.manifest.read_text()))

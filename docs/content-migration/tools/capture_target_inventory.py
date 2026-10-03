"""Capture repository canonical identities via AST and optional local public GETs only."""
import ast, json, re, unicodedata, urllib.request, urllib.parse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parents[1]/'evidence'
def slug(name):
    return re.sub('[^a-z0-9]+','-',unicodedata.normalize('NFKD',name.strip()).encode('ascii','ignore').decode().lower()).strip('-')[:140].rstrip('-')
def constants(file,var):
    tree=ast.parse(file.read_text(encoding='utf8'))
    for n in tree.body:
        if isinstance(n,ast.AnnAssign) and isinstance(n.target,ast.Name) and n.target.id==var: return ast.literal_eval(n.value)
def records(folder,call):
    result=[]
    for file in sorted(folder.glob('*.py')):
        tree=ast.parse(file.read_text(encoding='utf8'))
        for n in ast.walk(tree):
            if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id==call:
                record={'source_file':str(file.relative_to(ROOT)).replace('\\','/')}
                for k in n.keywords:
                    try: record[k.arg]=ast.literal_eval(k.value)
                    except (ValueError,TypeError): pass
                record['slug']=record.get('slug') or slug(record.get('name') or record['title'])
                result.append(record)
    return result
snapshot={'observed_on':'2026-10-03','source':'repository AST; no database connection',
 'districts':[{'name':n,'slug':s,'division':d} for n,s,d in constants(ROOT/'backend/app/data/maharashtra.py','MAHARASHTRA_DISTRICTS_V1')],
 'interests':[{'name':n,'slug':s,'display_order':d} for n,s,d in constants(ROOT/'backend/app/data/interests.py','MAHARASHTRA_INTERESTS_V1')],
 'curated_places':records(ROOT/'backend/app/data/places','CuratedPlace'),
 'curated_stories':records(ROOT/'backend/app/data/discovery_stories','CuratedDiscoveryStory')}
OUT.mkdir(parents=True,exist_ok=True)
OUT.joinpath('repository-canonical-entities.json').write_text(json.dumps(snapshot,ensure_ascii=False,indent=2),encoding='utf8')
print({k:len(snapshot[k]) for k in ['districts','interests','curated_places','curated_stories']})
# Only the configured loopback public API can be inspected. No auth and no mutations.
env=ROOT/'frontend/.env.local'
m=re.search(r'^NEXT_PUBLIC_API_URL\s*=\s*[\"\']?([^\s\"\']+)',env.read_text(encoding='utf8'),re.M) if env.exists() else None
api=m.group(1).rstrip('/') if m else None
live={'observed_on':'2026-10-03','scope':'local public API; excludes drafts/unpublished and is NOT a production database export','responses':[]}
if api and urllib.parse.urlsplit(api).hostname in {'localhost','127.0.0.1','::1'}:
    for path in ['/destinations','/interests','/places?limit=100&offset=0','/discovery-stories?limit=100&offset=0']+['/destinations/'+d['slug']+'/places' for d in snapshot['districts']]:
        try:
            with urllib.request.urlopen(api+path,timeout=10) as r: response={'path':path,'status':r.status,'data':json.load(r)}
        except Exception as e: response={'path':path,'error':str(e)}
        live['responses'].append(response)
        print(path,response.get('status',response.get('error')),flush=True)
else: live['limitation']='No configured loopback public API; no production URL queried'
OUT.joinpath('local-public-discovery-snapshot.json').write_text(json.dumps(live,ensure_ascii=False,indent=2),encoding='utf8')

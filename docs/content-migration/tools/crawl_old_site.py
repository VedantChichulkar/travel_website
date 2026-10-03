"""Read-only old-site inventory; never fetches images or writes to application data."""
import json, re, time, urllib.request, urllib.error, urllib.parse
from collections import defaultdict
from pathlib import Path
from bs4 import BeautifulSoup

BASE = 'https://maharashtratouristplaces.in/'
OUT = Path(__file__).resolve().parents[1] / 'evidence'
ALLOWED = {'maharashtratouristplaces.in', 'www.maharashtratouristplaces.in'}
ASSET = re.compile(r'\.(?:jpe?g|png|webp|gif|svg|ico|pdf|mp4|mp3|zip|css|js|woff2?|ttf)(?:$|\?)', re.I)
HEADERS = {'User-Agent': 'MaharashtraTouristPlaces-MigrationInventory/1.0 (read-only owner-requested audit)'}

def norm(url, parent=BASE):
    u = urllib.parse.urlsplit(urllib.parse.urljoin(parent,url))
    if u.scheme not in {'http','https'} or u.hostname not in ALLOWED: return None
    if ASSET.search(u.path) or '/wp-content/' in u.path or '/wp-admin' in u.path or '/wp-includes/' in u.path: return None
    if u.query and not re.search(r'^(?:page|paged)=\d+$',u.query): return None
    path = re.sub(r'/+', '/',u.path) or '/'
    return urllib.parse.urlunsplit(('https','maharashtratouristplaces.in',path,u.query,''))

def fetch(url):
    started = time.time()
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers=HEADERS),timeout=30) as r:
            ctype=r.headers.get('Content-Type','')
            if not any(s in ctype for s in ('text/','xml','json')): return {'url':url,'status':r.status,'error':'Non-text response; body not read','content_type':ctype}
            text=r.read(4_000_000).decode('utf-8','replace')
            return {'url':url,'final_url':r.url,'status':r.status,'content_type':ctype,'text':text,'elapsed_seconds':round(time.time()-started,2)}
    except Exception as e: return {'url':url,'status':getattr(e,'code',None),'error':str(e)}

def text(node): return node.get_text(' ',strip=True) if node else ''

def parse_page(result):
    raw=result.pop('text')
    soup=BeautifulSoup(raw, 'html.parser')
    unescaped=raw.replace('\\/', '/')
    result['referenced_image_urls']=sorted(set(re.findall(r'https?://[^\s<>\"\']+?\.(?:jpe?g|png|webp|gif|svg)(?:\?[^\s<>\"\']*)?', unescaped, re.I)))
    result['gallery_images']=[]
    for n in soup.select('[data-thumbnail], [data-background-image], [data-full], [data-image]'):
        result['gallery_images'].append({'attributes':dict(n.attrs),'caption':text(n),'parent_context':text(n.parent)[:300]})
    result['background_settings']=[]
    for n in soup.select('[data-settings]'):
        try:
            settings=json.loads(n['data-settings'])
            if 'image' in n['data-settings'] or 'background' in n['data-settings']: result['background_settings'].append(settings)
        except ValueError: pass
    result['title']=text(soup.title)
    result['canonical_url']=(soup.select_one('link[rel="canonical"]') or {}).get('href','')
    result['robots']=(soup.select_one('meta[name="robots"]') or {}).get('content','')
    result['meta_description']=(soup.select_one('meta[name="description"]') or {}).get('content','')
    result['headings']=[{'level':n.name,'text':text(n)} for n in soup.select('h1,h2,h3,h4')]
    result['links']=[{'url':urllib.parse.urljoin(result['url'],n['href']),'text':text(n)} for n in soup.select('a[href]')]
    result['json_ld']=[]
    for n in soup.select('script[type="application/ld+json"]'):
        try: result['json_ld'].append(json.loads(n.string or n.get_text()))
        except ValueError: pass
    result['images']=[]
    for n in soup.select('img,source'):
        item={'tag':n.name,'attributes':dict(n.attrs)}
        figure=n.find_parent('figure')
        item['caption']=text(figure.find('figcaption')) if figure else ''
        item['context']=text(n.find_parent(['article','figure']))[:500] if n.find_parent(['article','figure']) else ''
        result['images'].append(item)
    result['css_image_urls']=sorted(set(re.findall(r'url\([\s\'"]*([^\)\'"\s]+)',str(soup))))
    result['faqs']=[]
    for n in soup.select('.elementor-accordion-item,.elementor-toggle-item,details'):
        q=n.select_one('.elementor-tab-title,summary')
        a=n.select_one('.elementor-tab-content')
        result['faqs'].append({'question':text(q),'answer':text(a) or text(n).removeprefix(text(q)).strip()})
    main=soup.select_one('.entry-content') or soup.select_one('main') or soup.body
    for n in main.select('script,style,nav,footer'): n.decompose()
    result['content_blocks']=[{'tag':n.name,'text':text(n)} for n in main.select('h1,h2,h3,h4,h5,p,li,td,dt,dd') if text(n)]
    result['content_text']=main.get_text('\n',strip=True)
    return result

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    infra=[]; sitemap_urls=[]
    for url in [BASE+'robots.txt',BASE+'sitemap_index.xml',BASE+'wp-sitemap.xml',BASE+'sitemap.xml']:
        r=fetch(url); infra.append(r)
        if 'text' in r:
            sitemap_urls += re.findall(r'^Sitemap:\s*(\S+)',r['text'],re.M|re.I)
            if 'xml' in r.get('content_type',''): sitemap_urls += re.findall(r'<loc>(.*?)</loc>',r['text'])
        time.sleep(.25)
    robots=infra[0].get('text','')
    # Respect public robot exclusions for this bounded crawl.
    disallowed=[m for m in re.findall(r'^Disallow:\s*(\S+)',robots,re.M|re.I) if m]
    queue=[BASE]; queued={BASE}; parents=defaultdict(set)
    seen_sitemaps=set()
    while sitemap_urls:
        url=sitemap_urls.pop(0)
        if url in seen_sitemaps or urllib.parse.urlsplit(url).hostname not in ALLOWED: continue
        seen_sitemaps.add(url)
        if not url.endswith('.xml'):
            u=norm(url)
            if u and u not in queued: queue.append(u); queued.add(u); parents[u].add('sitemap')
            continue
        prior=next((r for r in infra if r['url']==url),None)
        r=prior or fetch(url)
        if not prior: infra.append(r)
        if 'text' in r: sitemap_urls += re.findall(r'<loc>(.*?)</loc>',r['text'])
        time.sleep(.25)
    pages=[]; visited=set()
    while queue and len(visited)<200:
        url=queue.pop(0)
        if url in visited: continue
        visited.add(url)
        path=urllib.parse.urlsplit(url).path
        if any(path.startswith(d) for d in disallowed if d!='/'): pages.append({'url':url,'status':None,'error':'robots exclusion','discovered_from':sorted(parents[url])}); continue
        r=fetch(url); r['discovered_from']=sorted(parents[url])
        if 'text' in r and 'html' in r.get('content_type',''):
            r=parse_page(r)
            for link in r['links']:
                u=norm(link['url'],url)
                if u:
                    parents[u].add(url)
                    if u not in queued: queue.append(u); queued.add(u)
        else: r.pop('text',None)
        pages.append(r)
        print(len(pages),r.get('status'),url,flush=True)
        OUT.joinpath('old-site-pages.json').write_text(json.dumps(pages,ensure_ascii=False,indent=2),encoding='utf-8')
        time.sleep(.35)
    OUT.joinpath('crawl-infrastructure.json').write_text(json.dumps(infra,ensure_ascii=False,indent=2),encoding='utf-8')
    OUT.joinpath('crawl-summary.json').write_text(json.dumps({'observed_on':'2026-10-03','pages_requested':len(pages),'remaining_queue':queue,'discovered_unique_urls':len(queued),'sitemap_urls_seen':sorted(seen_sitemaps),'parents':{k:sorted(v) for k,v in parents.items()},'image_bytes_downloaded':0,'limit':200},ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__': main()

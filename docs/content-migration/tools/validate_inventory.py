"""Offline QA for mapping artifacts; no network, DB, image retrieval or application mutation."""
import csv,json,re,xml.etree.ElementTree as ET
from pathlib import Path
from collections import Counter,defaultdict
from urllib.parse import urlsplit
from crawl_old_site import norm
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence'
load=lambda name:json.loads((E/name).read_text(encoding='utf8'))
def read_csv(name):
 with (ROOT/name).open(encoding='utf8',newline='') as f:return list(csv.DictReader(f))
content=read_csv('content-migration-inventory.csv');images=read_csv('image-migration-inventory.csv')
mapping=load('review-mapping-data.json');pages=load('old-site-pages.json');summary=load('crawl-summary.json');repo=load('repository-canonical-entities.json');live=load('local-public-discovery-snapshot.json');counts=load('inventory-counts.json')
results=[]
def check(name,condition):
 if not condition: raise AssertionError(name)
 results.append({'check':name,'result':'PASS'})
check('44 unique content URLs',len(content)==44==len({r['old_url'] for r in content}))
check('44 unique canonical URLs',len({r['old_canonical_url'] for r in content})==44)
check('CSV content values exactly match reviewed data',content==[{k:str(v) if v is not None else '' for k,v in r.items()} for r in mapping['content_records']])
check('CSV image values exactly match reviewed data',images==[{k:str(v) if v is not None else '' for k,v in r.items()} for r in mapping['image_records']])
check('No ragged CSV rows',all(None not in r for r in content+images))
check('Crawl exhausted its discovered URL queue',not summary['remaining_queue'] and summary['pages_requested']==summary['discovered_unique_urls']==44)
check('All public HTML reads returned 200 within old-site host',all(p['status']==200 and urlsplit(p.get('final_url','')).hostname=='maharashtratouristplaces.in' for p in pages))
visited={p['url'] for p in pages}
internal={u for p in pages for l in p['links'] if (u:=norm(l['url'],p['url']))}
check('Every normalized discovered internal HTML link processed',not (internal-visited))
ns={'s':'http://www.sitemaps.org/schemas/sitemap/0.9','i':'http://www.google.com/schemas/sitemap-image/1.1'}
infra=load('crawl-infrastructure.json');xml=ET.fromstring(next(r['text'] for r in infra if r['url'].endswith('/page-sitemap.xml')))
sitemap={n.text for n in xml.findall('s:url/s:loc',ns)}
check('All 42 sitemap pages processed',len(sitemap)==42 and sitemap<=visited)
link_only=sorted(visited-sitemap)
check('Two link-only omissions captured',len(link_only)==2 and any('/gandhi-sagar-park/' in u for u in link_only) and any(u.endswith('/khuldabad/') for u in link_only))
check('All sitemap image declarations inventoried',all((n.findtext('s:loc',namespaces=ns),i.text) in {(r['source_page_url'],r['original_image_url_path']) for r in images} for n in xml.findall('s:url',ns) for i in n.findall('i:image/i:loc',ns)))
check('Full repository baseline recorded',(len(repo['districts']),len(repo['interests']),len(repo['curated_places']),len(repo['curated_stories']))==(36,9,49,10))
check('Local public snapshot contains no failed reads',all(r.get('status')==200 for r in live['responses']))
check('All 36 public Destination lists captured',len([r for r in live['responses'] if r['path'].endswith('/places')])==36)
check('Local public lists have no published Destinations',sum(len(r['data']['items']) for r in live['responses'] if r['path'].endswith('/places'))==0)
districts={r['slug'] for r in repo['districts']};interests={r['slug'] for r in repo['interests']}
places=[r for r in content if r['proposed_entity_type']=='PLACE'];dest=[r for r in content if r['proposed_entity_type']=='DESTINATION']
check('17 Places and six Destination candidates captured',len(places)==17 and len(dest)==6)
check('Every proposed Place has a canonical District',all(r['proposed_district_slug'] in districts for r in places))
check('No second Interest taxonomy used',all(set(filter(None,r['interest_slugs'].split(';')))<=interests for r in content))
check('No duplicate proposed Place district/slug identities',len({(r['proposed_district_slug'],r['proposed_slug']) for r in places})==len(places))
parents={(r['proposed_district_slug'],r['proposed_destination_slug']) for r in dest}
check('All proposed Destination assignments resolve in same District',all(not r['proposed_destination_slug'] or (r['proposed_district_slug'],r['proposed_destination_slug']) in parents for r in places))
check('Uncertain Harihar/Ambhora Destination assignments remain empty',all(not r['proposed_destination_slug'] for r in places if 'Harihar' in r['proposed_canonical_name'] or 'Ambhora' in r['proposed_canonical_name']))
check('All 17 About texts and source FAQ sets captured',all(r['main_description_about'] and json.loads(r['faqs_json']) for r in places))
check('All Place operational claims marked unverified/volatile',all(r['potentially_volatile']=='YES' and r['verification_status']=='OLD_SITE_UNVERIFIED' for r in places))
curated={r['name']:r for r in repo['curated_places']};matches=[r for r in places if r['existing_matching_entity']]
check('Four curated matches preserve existing scoped slugs',len(matches)==4 and all(r['proposed_slug']==curated[r['existing_matching_entity']]['slug'] and r['proposed_district_slug']==curated[r['existing_matching_entity']]['district_slug'] for r in matches))
check('Lake/Park unresolved pair has no automatic create/merge',len([r for r in places if r['collision_action']=='POSSIBLE_DUPLICATE'])==2)
u=[r for r in places if r['proposed_destination']=='Umred']
check('Complete four-Place Umred pilot and 31 FAQ pairs',len(u)==4 and sum(int(r['unique_faq_count']) for r in u)==31)
check('142 raw / 140 unique-within-page FAQs reconciled',sum(int(r['raw_faq_count']) for r in content)==142 and sum(int(r['unique_faq_count']) for r in content)==140)
check('486 unique image page/URL rows and 237 exact URLs',len(images)==len({(r['source_page_url'],r['original_image_url_path']) for r in images})==486 and len({r['original_image_url_path'] for r in images})==237)
check('124 approximate image filename families reconciled',len({r['filename_family_id'] for r in images})==124)
roles={'DESTINATION_HERO','DESTINATION_GALLERY','PLACE_HERO','PLACE_GALLERY','EDITORIAL','UNKNOWN'}
check('Every image role and source page is explicit',all(r['proposed_image_role'] in roles and r['source_page_url'] in visited and r['proposed_relationship'] for r in images))
place_targets={r['proposed_public_path'] for r in places};dest_targets={r['proposed_public_path'] for r in dest}
check('Image relationships resolve to mapped entity type',all(r['proposed_relationship'] in place_targets if r['proposed_image_role'].startswith('PLACE_') else r['proposed_relationship'] in dest_targets if r['proposed_image_role'].startswith('DESTINATION_') else r['proposed_relationship']=='UNKNOWN' for r in images))
check('All image rights require owner confirmation',all(r['rights_provenance_status']=='OWNER_CONFIRMATION_REQUIRED' for r in images))
check('JSON-valued CSV fields parse',all(json.loads(r['faqs_json']) is not None and json.loads(r['other_structured_information_json']) is not None and json.loads(r['source_reference_information_json']) is not None for r in content) and all(json.loads(r['related_variant_urls_json']) and json.loads(r['appears_on_pages_json']) for r in images))
check('CSV fields contain no accidental spreadsheet formulas',all(not v.startswith('=') for r in content+images for v in r.values()))
check('No image/binary files in artifact directory',not any(p.suffix.lower() in {'.jpg','.jpeg','.png','.webp','.gif','.svg','.pdf'} for p in ROOT.rglob('*') if p.is_file()))
check('Zero image bytes requested/recorded',summary['image_bytes_downloaded']==counts['image_bytes_downloaded']==0)
check('Requested five artifacts and repository map exist',all((ROOT/n).is_file() for n in ['old-site-inventory.md','content-migration-inventory.csv','image-migration-inventory.csv','migration-summary.md','umred-pilot-plan.md','repository-migration-map.md']))
check('No unfilled document templates',all('<!--' not in p.read_text(encoding='utf8') for p in ROOT.glob('*.md')))
report={'observed_on':'2026-10-03','checks':results,'check_count':len(results),'sitemap_pages':len(sitemap),'link_only_pages':link_only,'uncrawled_internal_urls':sorted(internal-visited),'csv_exact_roundtrip':'PASS (artifact-tool export builder)','image_bytes_downloaded':0,'application_changes':'NONE; docs/content-migration only'}
(E/'quality-checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(f'{len(results)} offline quality checks passed; all URL/hierarchy/CSV/media counts reconciled.')

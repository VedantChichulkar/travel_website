"""Build review-only mapping data from saved evidence. No network or database writes."""
import json,re,unicodedata,hashlib,html,xml.etree.ElementTree as ET
from pathlib import Path
from collections import defaultdict,Counter
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence'
BASE='https://maharashtratouristplaces.in'
pages=json.loads((E/'old-site-pages.json').read_text(encoding='utf8'))
repo=json.loads((E/'repository-canonical-entities.json').read_text(encoding='utf8'))
live=json.loads((E/'local-public-discovery-snapshot.json').read_text(encoding='utf8'))

def clean(s): return re.sub(r'\s+',' ',s.replace('\u200b','')).strip()
def slug(s): return re.sub('[^a-z0-9]+','-',unicodedata.normalize('NFKD',s.strip()).encode('ascii','ignore').decode().lower()).strip('-')[:140].rstrip('-')
def unique(seq): return list(dict.fromkeys(seq))
def dump(x): return json.dumps(x,ensure_ascii=False,separators=(',',':'))
district_names={x['slug']:x['name'] for x in repo['districts']}
D='chhatrapati-sambhajinagar'
# Only relationships supported by listing + page text are proposed. Tehsil != town.
destinations={
 '/chhatrapati-sambhaji-nagar/daulatabad-village/':('Daulatabad',D,'Village overview with explicit district and linked fort.'),
 '/chhatrapati-sambhaji-nagar/verul/':('Verul',D,'Village overview explicitly identifies Khuldabad tehsil. Flatten to District -> Verul; do not nest Destinations.'),
 '/chhatrapati-sambhaji-nagar/khuldabad/':('Khuldabad',D,'Old tehsil listing links Bhadra Maruti. Confirm intended Destination scope.'),
 '/nashik/trimbakeshwar/':('Trimbakeshwar','nashik','Listing mixes Trimbak town and wider tehsil. Town temples supported; Harihar parent held for review.'),
 '/nagpur/umred/':('Umred','nagpur','Old tehsil listing and all four attraction descriptions support Umred/Nagpur. Town versus wider planning-area scope needs owner review.'),
 '/nagpur/kuhi/':('Kuhi','nagpur','Tehsil listing, not proof that the Ambhora temple is in Kuhi town. Keep temple district-level pending planning-area decision.'),
}
# path, canonical name, district, Destination or None, existing curated identity or None, Interests, summary, notes
places=[
('/chhatrapati-sambhaji-nagar/daulatabad-village/daulatabad-fort/','Devgiri-Daulatabad Fort',D,'Daulatabad','Devgiri-Daulatabad Fort',['forts-heritage','history-architecture'],'Fort complex at Daulatabad, also named Devgiri in the old page.','Definite naming alias of curated fort; preserve existing slug and copy. Do not automatically attach existing district-only Place to a new Destination.'),
('/chhatrapati-sambhaji-nagar/verul/shree-laksha-vinayak-ganapati-temple-shree-kshetra-verul/','Shree Laksha Vinayak Ganapati Temple',D,'Verul',None,['sacred-spiritual'],'Ganesha temple described at Shree Kshetra Verul.','Attribute religious beliefs as traditions. Verify historical claims and name spelling.'),
('/chhatrapati-sambhaji-nagar/verul/shri-grishneshwar-jyotirlinga/','Ghrishneshwar Temple',D,'Verul','Ghrishneshwar Temple',['sacred-spiritual'],'Shiva pilgrimage temple at Verul near Ellora.','Grishneshwar/Ghrishneshwar/Jyotirlinga spelling aliases map to one curated Place. Old construction chronology conflicts with common accounts; retain curated copy until authoritative review.'),
('/chhatrapati-sambhaji-nagar/verul/ellora-caves/','Ellora Caves',D,'Verul','Ellora Caves',['ancient-caves','history-architecture','sacred-spiritual'],'Rock-cut cave complex at Verul with Hindu, Buddhist, and Jain heritage.','Existing curated Place. Do not split Kailasa/Kailash temple or individual caves into duplicates merely because mentioned in text.'),
('/chhatrapati-sambhaji-nagar/panchakki-water-mill/','Panchakki Water Mill',D,None,None,['history-architecture'],'Historic water-mill attraction in Chhatrapati Sambhajinagar.','District-level city attraction; no city Destination invented.'),
('/chhatrapati-sambhaji-nagar/verul/ahilyabai-holkar-shivalay-tirth-kund/','Ahilyabai Holkar Shivalay Tirth Kund',D,'Verul',None,['sacred-spiritual','history-architecture'],'Sacred tank associated with Ahilyabai Holkar at Verul.','Confirm Ahilyabai Holkar Talab/Shivalay Tirth Kund aliases are the same site.'),
('/chhatrapati-sambhaji-nagar/khuldabad/shree-bhadra-maruti-mandir/','Shree Bhadra Maruti Temple',D,'Khuldabad',None,['sacred-spiritual'],'Hanuman temple described at Khuldabad.','Temple/Mandir are name aliases within this page. Tehsil Destination scope remains proposed.'),
('/chhatrapati-sambhaji-nagar/bibi-ka-maqbara/','Bibi Ka Maqbara',D,None,None,['history-architecture'],'Mausoleum attraction described in Chhatrapati Sambhajinagar.','District-level city attraction. Verify historical authorship and patronage instead of transferring old copy as fact.'),
('/nashik/trimbakeshwar/trimbakeshwar-jyotirlinga-temple/','Trimbakeshwar Temple','nashik','Trimbakeshwar','Trimbakeshwar Temple',['sacred-spiritual'],'Shiva pilgrimage temple in Trimbak, Nashik district.','Trimbakeshwar/Jyotirlinga/Trimbkeshwar are aliases. Preserve curated slug and descriptions; verify temple-access rules separately.'),
('/nashik/trimbakeshwar/shri-gajanan-maharaj-sansthan-trimbkeshwar/','Shri Gajanan Maharaj Sansthan, Trimbakeshwar','nashik','Trimbakeshwar',None,['sacred-spiritual'],'Religious institution described at Trimbakeshwar.','Distinct from Gajanan Maharaj WCL Umred site. Do not import lodging tariffs, room booking, or meals as hotel inventory.'),
('/nashik/trimbakeshwar/harihar-fort/','Harihar Fort','nashik',None,None,['forts-heritage','nature-hills'],'Hill fort near Harshewadi and Nirgudpada in Trimbakeshwar tehsil.','Old category groups it under Trimbakeshwar, but page locates trek starts in Harshewadi/Nirgudpada. Keep Destination null pending scope decision. Safety/access and monsoon advice require authority review.'),
('/nagpur/shri-ganesh-mandir-tekdi/','Shri Ganesh Mandir Tekdi','nagpur',None,None,['sacred-spiritual'],'Ganesha temple near Nagpur railway station.','Nagpur city Place remains district-level; do not create a Nagpur child Destination just to fill a parent.'),
('/nagpur/umred/shree-gajanan-maharaj-devasthan-w-c-l-picnic-spot/','Shree Gajanan Maharaj Devasthan WCL, Umred','nagpur','Umred',None,['sacred-spiritual','nature-hills'],'Temple and picnic setting described near Gangapur in the Umred WCL area.','Confirm public access with temple/WCL management. Do not split the onsite Shiva shrine or picnic area into separate Places without evidence.'),
('/nagpur/umred/gandhi-sagar-lake/','Gandhi Sagar Lake, Umred','nagpur','Umred',None,['nature-hills'],'Lake also called Gaotalav/Gaon Talav in Umred, with a nearby Shiva shrine described in the old text.','Check relationship to Gandhi Sagar Park before creation. Keep separate provisional identities; name/proximity is not proof of duplication. Avoid confusing with similarly named Nagpur city lake.'),
('/nagpur/umred/shree-vitthal-rukmini-ganeshrao-maharaj-devasthan-kawrapeth/','Shree Vitthal Rukmini Ganeshrao Maharaj Devasthan, Kawrapeth','nagpur','Umred',None,['sacred-spiritual'],'Temple described in Kawrapeth in Umred taluka.','Distinct from curated Shri Vitthal-Rukmini Temple, Pandharpur in Solapur. Cross-district name similarity must not cause a merge.'),
('/nagpur/kuhi/shree-chaitanyeshwar-temple/','Shree Chaitanyeshwar Shiv Temple, Ambhora','nagpur',None,None,['sacred-spiritual'],'Shiva temple described in Ambhora village within Kuhi tehsil.','Old title says Amhora and body/heading say Ambhora. Village spelling and location need review. Kuhi town parent is not established; do not invent Ambhora Destination or split onsite smaller shrines.'),
('/nagpur/umred/gandhi-sagar-park/','Gandhi Sagar Park, Umred','nagpur','Umred',None,['nature-hills'],'Public park described in Budhwari Peth, Umred.','Relationship/boundary review with Gandhi Sagar Lake. Distinct old URLs, addresses and galleries support retaining two candidates until verified; do not merge automatically.'),
]
place_defs={x[0]:x for x in places}
listing_paths={'/temples/':('sacred-spiritual','/explore/sacred-spiritual'),'/forts/':('forts-heritage','/explore/forts-heritage'),'/caves/':('ancient-caves','/explore/ancient-caves'),'/all-updates/':('','/destinations')}
active_districts={'/nagpur/':'nagpur','/nashik/':'nashik','/chhatrapati-sambhaji-nagar/':D}
empty_districts={'/pune/':'pune','/amravati/':'amravati','/bhandara/':'bhandara','/chandrapur/':'chandrapur','/gondia/':'gondia','/wardha/':'wardha'}
live_destinations=[]
for r in live['responses']:
 if r['path'].endswith('/places') and r.get('data'): live_destinations.extend(r['data'].get('items',[]))
curated={x['name']:x for x in repo['curated_places']}
content=[]

def sections(page):
 out=defaultdict(list); current='INTRODUCTION'
 for b in page.get('content_blocks',[]):
  if b['tag'] in ('h1','h2'): current=clean(b['text']).upper()
  elif b['text'] not in out[current]: out[current].append(b['text'])
 return dict(out)
def faq_field(faqs,pattern):
 return '\n'.join(unique(f"{f['question']} {f['answer']}" for f in faqs if re.search(pattern,f['question'],re.I)))
for index,p in enumerate(sorted(pages,key=lambda x:x['url'])):
 path=p['url'].removeprefix(BASE); sect=sections(p); raw_faqs=p.get('faqs',[])
 faqs=[]; seen=set()
 for f in raw_faqs:
  key=(clean(f['question']).casefold(),clean(f['answer']).casefold())
  if key not in seen: faqs.append(f);seen.add(key)
 headings=[b['text'] for b in p.get('content_blocks',[]) if b['tag'] in ('h1','h2')]
 row={'record_id':f'C{index+1:03}','old_page_title':p.get('title',''),'old_page_heading':headings[0] if headings else '',
      'old_url':p['url'],'old_canonical_url':p.get('canonical_url',''),'http_status':p.get('status',''),
      'content_presence':'CONTENT' if p.get('content_text','').strip() else 'EMPTY_PLACEHOLDER',
      'proposed_entity_type':'OTHER / REVIEW REQUIRED','proposed_district':'','proposed_district_slug':'','proposed_destination':'','proposed_destination_slug':'',
      'proposed_canonical_name':'','proposed_slug':'','proposed_public_path':'','hierarchy_evidence':'',
      'existing_matching_entity':'','existing_match_source':'','collision_action':'SKIP','collision_notes':'',
      'interest_slugs':'','short_summary':'','main_description_about':'\n'.join(sect.get('ABOUT',[])) or (re.search(r'(?:^|\n)ABOUT\n(.*?)(?=\n(?:LOCATION|MAP|ADDRESS|TIMINGS|FAQ)(?:\n|$))',p.get('content_text',''),re.S|re.I).group(1).strip() if re.search(r'(?:^|\n)ABOUT\n(.*?)(?=\n(?:LOCATION|MAP|ADDRESS|TIMINGS|FAQ)(?:\n|$))',p.get('content_text',''),re.S|re.I) else ''),
      'address':'\n'.join(sect.get('ADDRESS',sect.get('ADDERESS',[]))),
      'opening_hours':'\n'.join(unique(v for k,vs in sect.items() if 'TIMING' in k for v in vs)),
      'entry_fee':'\n'.join(unique(v for k,vs in sect.items() if 'FEE' in k for v in vs)) or faq_field(faqs,r'entry fee|entrance fee|entry ticket'),
      'recommended_duration':faq_field(faqs,r'how long.*(?:trek|visit)|(?:how much time.*visit)|time.*needed.*explore|duration'),
      'best_time_to_visit':faq_field(faqs,r'best.*(?:time|season)|(?:time|season).*best'),
      'getting_there':faq_field(faqs,r'how.*reach|how.*go|public transport|catch.*bus|go.*bus|go.*travels|can we go'),
      'railway_information':'\n'.join(unique(f"{f['question']} {f['answer']}" for f in faqs if re.search('railway|station|train',f['question']+' '+f['answer'],re.I))),
      'airport_information':'\n'.join(unique(f"{f['question']} {f['answer']}" for f in faqs if re.search('airport|flight',f['question']+' '+f['answer'],re.I))),
      'faqs_json':dump(faqs),'raw_faq_count':len(raw_faqs),'unique_faq_count':len(faqs),
      'other_structured_information_json':dump({'sections':sect,'meta_description':p.get('meta_description',''),'source_content_evidence':f"evidence/old-site-pages.json: {p['url']}"}),
      'source_reference_information_json':dump({'old_site_source':p['url'],'external_links':unique(l['url'] for l in p.get('links',[]) if l['url'].startswith(('http://','https://')) and 'maharashtratouristplaces.in' not in l['url']),'authority_verification':'NOT_PERFORMED'}),
      'potentially_volatile':'NO_STRUCTURED_CLAIMS_CAPTURED','volatile_fields':'','verification_status':'OLD_SITE_UNVERIFIED','observed_on':'2026-10-03',
      'migration_notes':'Inventory only. Blank fields mean not captured from this page, not verified absence. No import authorized.',
      'mapping_confidence':'NOT_APPLICABLE','review_status':'REVIEW_REQUIRED' if p.get('content_text','').strip() else 'EMPTY_PLACEHOLDER'}
 if path in place_defs:
  _,name,ds,dn,match,interests,summary,notes=place_defs[path]
  row.update(proposed_entity_type='PLACE',proposed_district_slug=ds,proposed_destination=dn or '',proposed_destination_slug=slug(dn) if dn else '',proposed_canonical_name=name,
             interest_slugs=';'.join(interests),short_summary=summary,mapping_confidence='HIGH_DISTRICT;PROPOSED_DESTINATION' if dn else 'HIGH_DISTRICT;DISTRICT_LEVEL',
             collision_action='ENRICH_EXISTING' if match else 'CREATE',review_status='REVIEW_REQUIRED',migration_notes=notes+' '+row['migration_notes'],
             hierarchy_evidence='Old page location text + nested listing/URL. Evidence is proposed geography, not independently verified coordinates.')
  if match:
   existing=curated[match]; row['existing_matching_entity']=match; row['existing_match_source']=existing['source_file']+'; repository dataset + local public API'; row['proposed_slug']=existing['slug']
   row['collision_notes']='Existing canonical identity. Field-level additive enrichment requires Admin ownership/version review; preserve curated content and slug.'
  else:
   row['proposed_slug']=slug(name);row['collision_notes']='No match among 49 curated Places, 10 Stories, or local public catalogue. Check unpublished/Admin and production records before CREATE.'
  if path.endswith(('/gandhi-sagar-lake/','/gandhi-sagar-park/')):
   row['collision_action']='POSSIBLE_DUPLICATE';row['collision_notes']='Lake/park relationship review only. No existing canonical match. Separate pages do not prove separate managed POIs; no merge or create decision yet.'
  row['proposed_public_path']=f"/places/{ds}/{row['proposed_slug']}"
 elif path in destinations:
  name,ds,evidence=destinations[path]
  row.update(proposed_entity_type='DESTINATION',proposed_district_slug=ds,proposed_destination=name,proposed_destination_slug=slug(name),proposed_canonical_name=name,proposed_slug=slug(name),proposed_public_path=f'/destinations/{ds}/{slug(name)}',hierarchy_evidence=evidence,collision_action='CREATE',mapping_confidence='PROPOSED;OWNER_SCOPE_REVIEW',review_status='REVIEW_REQUIRED',short_summary=p.get('meta_description',''),main_description_about=p['content_text'],collision_notes='No published Destination in local API across all 36 districts. Production/unpublished Admin collision check remains required.',migration_notes=evidence+' '+row['migration_notes'])
 elif path in active_districts:
  ds=active_districts[path];row.update(proposed_entity_type='DISTRICT',proposed_district_slug=ds,proposed_canonical_name=district_names[ds],proposed_slug=ds,proposed_public_path=f'/destinations/{ds}',existing_matching_entity=district_names[ds],existing_match_source='backend/app/data/maharashtra.py; local public API',collision_action='ENRICH_EXISTING',mapping_confidence='HIGH',hierarchy_evidence='Old district listing and canonical district registry.',migration_notes='Reuse canonical District. This inventory does not authorize edits to District records. Do not create duplicate district or city Destination.')
 elif path in empty_districts:
  ds=empty_districts[path];row.update(proposed_district_slug=ds,proposed_canonical_name=district_names[ds],existing_matching_entity=district_names[ds],existing_match_source='backend/app/data/maharashtra.py',migration_notes='Empty old placeholder. Reuse existing District if future content is supplied; no entity/content import proposed.')
 elif path=='/mumbai/':
  row.update(proposed_canonical_name='Mumbai',review_status='REVIEW_REQUIRED',migration_notes='Empty placeholder. Mumbai City versus Mumbai Suburban cannot be resolved from this page. Do not invent a District assignment.')
 elif path=='/chhatrapati-sambhaji-nagar/soegaon/':
  row.update(proposed_district_slug=D,proposed_canonical_name='Soegaon',migration_notes='Empty subarea placeholder; no Destination proposed without content and geographic scope review.')
 elif path in listing_paths:
  interest,target=listing_paths[path]; row.update(interest_slugs=interest,proposed_public_path=target,short_summary='Existing category/discovery listing, not a new entity.',migration_notes='Reuse canonical Interest route or destination directory. Preserve relevant attraction links in inventory; generic listing FAQs need editorial review and do not become a new Story or taxonomy.')
 elif path=='/': row.update(proposed_public_path='/destinations',migration_notes='Old homepage is a discovery index. Do not import as a Place, Destination or Story.')
 else: row.update(migration_notes='Utility/about/legal/contact page. Separate editorial/legal review if ever needed; no tourism entity or policy replacement proposed.')
 if row['proposed_district_slug']: row['proposed_district']=district_names[row['proposed_district_slug']]
 if row['proposed_entity_type']=='PLACE':
  volatile=[key for key in ['address','opening_hours','entry_fee','recommended_duration','best_time_to_visit','getting_there','railway_information','airport_information'] if row[key]]
  volatile.extend(['access_rules_and_safety','review_counts_and_ratings','faq_operational_claims'])
  row['potentially_volatile']='YES';row['volatile_fields']=';'.join(volatile)
 elif row['proposed_entity_type']=='DESTINATION' and row['short_summary']:
  row['potentially_volatile']='REVIEW_MARKETING_AND_ACCESS_CLAIMS';row['volatile_fields']='metadata_claims'
 if len(raw_faqs)!=len(faqs): row['migration_notes']+=f' Removed {len(raw_faqs)-len(faqs)} exact duplicate FAQ occurrence(s) in inventory view; raw evidence preserved.'
 if row['collision_action']=='SKIP' and path!='/mumbai/': row['review_status']='SKIP' if row['content_presence']=='CONTENT' else 'EMPTY_PLACEHOLDER'
 content.append(row)

by_url={r['old_url']:r for r in content}
# Every image occurrence is keyed by source page + exact referenced URL. Families only suggest duplication.
def family(url):
 from urllib.parse import urlsplit,unquote
 u=urlsplit(html.unescape(url));path=unquote(u.path)
 return u.netloc.lower()+re.sub(r'-\d+x\d+(?=\.[^.]+$)','',path)
def walk(x):
 if isinstance(x,dict):
  yield x
  for v in x.values(): yield from walk(v)
 elif isinstance(x,list):
  for v in x: yield from walk(v)
image_uses={};gallery_owners=defaultdict(set);primary_owners=defaultdict(set)
def add(page,url,method,attrs=None,caption='',context=''):
 if not url or not re.search(r'\.(jpe?g|png|webp|gif|svg)(?:\?|$)',url,re.I):return
 from urllib.parse import urljoin
 url=html.unescape(urljoin(page['url'],url))
 key=(page['url'],url)
 item=image_uses.setdefault(key,{'url':url,'page':page,'methods':set(),'alt':set(),'caption':set(),'width':set(),'height':set(),'contexts':set()})
 item['methods'].add(method)
 attrs=attrs or {}
 for val in [attrs.get('alt',''),attrs.get('aria-label','')]:
  if val:item['alt'].add(val)
 if caption:item['caption'].add(caption)
 if context:item['contexts'].add(context)
 for k in ['width','height']:
  val=attrs.get(k) or attrs.get('data-'+k)
  if val: item[k].add(str(val))
 owner=by_url[page['url']]
 if method=='ELEMENTOR_GALLERY' and owner['proposed_entity_type']=='PLACE':gallery_owners[family(url)].add(page['url'])
 if method=='SCHEMA_PRIMARY_IMAGE' and owner['proposed_entity_type'] in ['PLACE','DESTINATION']:primary_owners[family(url)].add(page['url'])
for p in pages:
 for u in p.get('referenced_image_urls',[]):add(p,u,'HTML_REFERENCE')
 for n in p.get('images',[]):
  attrs=n['attributes']
  for key in ['src','data-src','data-lazy-src']:add(p,attrs.get(key),'IMG',attrs,n.get('caption',''),n.get('context',''))
  for key in ['srcset','data-srcset','data-lazy-srcset']:
   for part in attrs.get(key,'').split(','):add(p,part.strip().split(' ')[0] if part.strip() else '', 'SRCSET')
 for n in p.get('gallery_images',[]):
  attrs=n['attributes']
  for key in ['data-thumbnail','data-background-image','data-full','data-image']:add(p,attrs.get(key),'ELEMENTOR_GALLERY',attrs,n.get('caption',''))
 for u in p.get('css_image_urls',[]): add(p,u,'INLINE_CSS')
 for obj in walk(p.get('background_settings',[])):
  if obj.get('url'):add(p,obj['url'],'ELEMENTOR_BACKGROUND')
 for obj in walk(p.get('json_ld',[])):
  if obj.get('@type')=='ImageObject':add(p,obj.get('contentUrl') or obj.get('url'),'SCHEMA_PRIMARY_IMAGE',obj,obj.get('caption',''))
  if obj.get('thumbnailUrl'):add(p,obj['thumbnailUrl'],'SCHEMA_THUMBNAIL')
# Include sitemap image references even when not visible in page's body.
ns={'s':'http://www.sitemaps.org/schemas/sitemap/0.9','i':'http://www.google.com/schemas/sitemap-image/1.1'}
for infra in json.loads((E/'crawl-infrastructure.json').read_text(encoding='utf8')):
 try: root=ET.fromstring(infra.get('text',''))
 except ET.ParseError: continue
 for n in root.findall('s:url',ns):
  url=n.findtext('s:loc',namespaces=ns)
  page=next((p for p in pages if p['url']==url),None)
  if page:
   for u in n.findall('i:image/i:loc',ns):add(page,u.text,'SITEMAP_IMAGE')
fam_urls=defaultdict(set);fam_pages=defaultdict(set)
for (page,u),item in image_uses.items():fam_urls[family(u)].add(u);fam_pages[family(u)].add(page)
image_rows=[]
for idx,((page_url,u),item) in enumerate(sorted(image_uses.items())):
 f=family(u);page_owner=by_url[page_url];owners=gallery_owners[f] or primary_owners[f]
 associated=by_url[next(iter(owners))] if len(owners)==1 else None
 role='UNKNOWN';relationship='UNKNOWN';notes=[]
 if associated:
  relationship=associated['proposed_public_path']
  if associated['proposed_entity_type']=='DESTINATION': role='DESTINATION_HERO' if associated['old_url'] in primary_owners[f] else 'DESTINATION_GALLERY'
  else:role='PLACE_HERO' if associated['old_url'] in primary_owners[f] else 'PLACE_GALLERY'
  notes.append('Proposed role inferred from old gallery/primary-image metadata. No visual identity, rights, integrity, or suitability verification performed.')
  if associated['proposed_canonical_name']=='Gandhi Sagar Lake, Umred':
   role='PLACE_HERO' if 'side-view1' in f else 'PLACE_GALLERY'
   notes.append('Lake hero candidate uses the named lake-side view family. Old primary metadata uses a Shiva-temple image; keep that as gallery context pending visual review.')
  if associated['proposed_canonical_name']=='Shree Gajanan Maharaj Devasthan WCL, Umred':
   role='PLACE_HERO' if 'temple-picnic-spot-wcl-umred.' in f else 'PLACE_GALLERY'
   notes.append('Temple-view family is the proposed hero candidate. Old primary video-point landscape remains a gallery candidate; visually confirm both before approval.')
  if page_url!=associated['old_url']:notes.append('Image reused on listing/related card; belongs to depicted Place/Destination, not automatically to source-page entity.')
 else:
  notes.append('No unique entity ownership supported by detail-gallery/primary-image evidence. Keep UNKNOWN until reviewed.')
 if re.search(r'-\d+x\d+\.[^.]+$',u):notes.append('WordPress resized variant; select approved original later, not a separate asset.')
 if '\u200b' in u:notes.append('Source URL contains a zero-width character. Preserve exact reference; safely encode during later approved retrieval.')
 if len(fam_pages[f])>1:notes.append('Same filename family appears on multiple pages; URL-level reuse only, not perceptual proof.')
 if re.search(r'-1\.[^.]+$',u):notes.append('Upload suffix -1 may be a duplicate upload. Bytes were not inspected; compare later before deduplication.')
 from urllib.parse import urlsplit,unquote
 file=unquote(urlsplit(u).path.rsplit('/',1)[-1]);base_files=[v for v in sorted(fam_urls[f]) if not re.search(r'-\d+x\d+\.[^.]+$',v)]
 image_rows.append({'image_record_id':f'I{idx+1:04}','source_page_url':page_url,'original_image_url_path':u,'filename':file,
 'associated_district':associated['proposed_district'] if associated else '', 'associated_district_slug':associated['proposed_district_slug'] if associated else '',
 'associated_destination':associated['proposed_destination'] if associated else '', 'associated_destination_slug':associated['proposed_destination_slug'] if associated else '',
 'associated_place':associated['proposed_canonical_name'] if associated and associated['proposed_entity_type']=='PLACE' else '',
 'associated_place_slug':associated['proposed_slug'] if associated and associated['proposed_entity_type']=='PLACE' else '',
 'proposed_relationship':relationship,'proposed_image_role':role,'alt_text':' | '.join(sorted(item['alt'])),'caption':' | '.join(sorted(item['caption'])),
 'format':file.rsplit('.',1)[-1].upper(),'declared_width':' | '.join(sorted(item['width'])),'declared_height':' | '.join(sorted(item['height'])),
 'dimension_source':'HTML/Elementor/schema declarations only; no file decoded' if item['width'] or item['height'] else 'NOT_AVAILABLE_WITHOUT_RETRIEVAL',
 'filename_family_id':hashlib.sha256(f.encode()).hexdigest()[:12],'filename_family_key':f,'observed_original_candidates_json':dump(base_files),
 'related_variant_urls_json':dump(sorted(fam_urls[f])),'appears_on_pages_json':dump(sorted(fam_pages[f])),
 'duplicate_relationship':'SAME_URL_OR_WORDPRESS_FILENAME_FAMILY;NOT_BYTE_VERIFIED' if len(fam_urls[f])>1 or len(fam_pages[f])>1 else 'NO_URL_DUPLICATE_IDENTIFIED',
 'discovery_methods':';'.join(sorted(item['methods'])),'rights_provenance_status':'OWNER_CONFIRMATION_REQUIRED','rights_evidence':'No per-image license, creator confirmation or usage permission established in this audit.',
 'possible_duplicate_upload_family_keys_json':dump(sorted(g for g in fam_urls if g!=f and re.sub(r'-\d+(?=\.[^.]+$)','',g)==re.sub(r'-\d+(?=\.[^.]+$)','',f))),
 'observed_on':'2026-10-03','migration_notes':' '.join(notes)+' Do not hotlink or import. Approved files must later enter existing PublicMediaAsset pipeline.'})

counts={'pages_discovered':len(content),'pages_http_200':sum(r['http_status']==200 for r in content),'empty_placeholders':sum(r['content_presence']=='EMPTY_PLACEHOLDER' for r in content),
 'proposed_destinations':sum(r['proposed_entity_type']=='DESTINATION' for r in content),'proposed_places':sum(r['proposed_entity_type']=='PLACE' for r in content),
 'district_pages_with_content':sum(r['proposed_entity_type']=='DISTRICT' for r in content),'proposed_discovery_stories':sum(r['proposed_entity_type']=='DISCOVERY STORY / EDITORIAL' for r in content),
 'actions':dict(Counter(r['collision_action'] for r in content)),
 'place_actions':dict(Counter(r['collision_action'] for r in content if r['proposed_entity_type']=='PLACE')),
 'existing_place_matches':sum(bool(r['existing_matching_entity']) for r in content if r['proposed_entity_type']=='PLACE'),
 'existing_district_matches_with_content':sum(bool(r['existing_matching_entity']) for r in content if r['proposed_entity_type']=='DISTRICT'),
 'existing_matches_including_empty_placeholders':sum(bool(r['existing_matching_entity']) for r in content),
 'local_published_destinations':len(live_destinations),'records_marked_review_required':sum(r['review_status']=='REVIEW_REQUIRED' for r in content),
 'place_records_with_volatile_information':sum(r['potentially_volatile']=='YES' for r in content),
 'faq_pairs_raw':sum(r['raw_faq_count'] for r in content),'faq_pairs_unique_within_pages':sum(r['unique_faq_count'] for r in content),
 'image_page_url_rows':len(image_rows),'distinct_image_urls':len({r['original_image_url_path'] for r in image_rows}),'image_filename_families':len(fam_urls),
 'image_families_reused_on_multiple_pages':sum(len(v)>1 for v in fam_pages.values()),'image_role_counts':dict(Counter(r['proposed_image_role'] for r in image_rows)),
 'rights_counts_rows':dict(Counter(r['rights_provenance_status'] for r in image_rows)),'image_bytes_downloaded':0,
 'umred_place_candidates':sum(r['proposed_entity_type']=='PLACE' and r['proposed_destination']=='Umred' for r in content),
 'umred_image_families':len({r['filename_family_id'] for r in image_rows if r['associated_destination']=='Umred'})}
(E/'review-mapping-data.json').write_text(json.dumps({'content_records':content,'image_records':image_rows,'counts':counts},ensure_ascii=False,indent=2),encoding='utf8')
(E/'inventory-counts.json').write_text(json.dumps(counts,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(counts,indent=2))

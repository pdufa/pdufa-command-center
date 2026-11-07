"""Retrieve frozen-TOP discovery documents; HTTP/NCT validation is not a grade."""
import concurrent.futures,datetime as dt,hashlib,html,json,pathlib,re,subprocess,urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1]
DATA=ROOT/'new-platform/frontend/data'
CACHE=pathlib.Path('/tmp/top-only-20261107/documents')
CACHE.mkdir(parents=True,exist_ok=True)
def main():
 ids={r['nctId'] for r in json.loads((DATA/'topOnlyBaseline20261107.json').read_text())['records']}
 leads=[]
 for batch in json.loads((DATA/'topOnlySourceSearch20261107.json').read_text())['batches']:
  for content in batch.get('result',{}).get('content',[]):
   if content.get('type')!='text':continue
   for block in content['text'].split('\n--------------------------------------------------------------------------------\n'):
    match=re.search(r'^(.+?) \((https?://[^\n]+)\)',block.strip())
    if not match:continue
    title,url=match.groups()
    if not any(term in url for term in ['.gov/Archives','investor','/ir.','ir.','gcs-web','q4cdn','/science','/scientific','/pipeline','/news-release','/press-release','/news/']):continue
    matched=[q['nctId'] for q in batch['queries'] if q['nctId'] in block]
    if matched:leads.append({'nctIds':matched,'title':title,'url':url})
 unique={r['url']:r for r in leads}
 def one(item):
  url,lead=item;key=hashlib.sha256(url.encode()).hexdigest();now=dt.datetime.now(dt.timezone.utc).isoformat()
  record={'url':url,'title':lead['title'],'candidateTopNcts':sorted(set(lead['nctIds'])&ids),'retrievedAt':now,'state':'UNVERIFIED_DOCUMENT_LEAD','cacheKey':key}
  try:
   req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (clinical-evidence-research)'})
   with urllib.request.urlopen(req,timeout=25) as response:raw=response.read();record.update(httpStatus=response.status,finalUrl=response.url)
   record.update(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
   if raw.startswith(b'%PDF'):
    source=CACHE/(key+'.pdf');source.write_bytes(raw)
    result=subprocess.run(['pdftotext','-layout',str(source),'-'],capture_output=True,text=True,timeout=20)
    if result.returncode:raise ValueError('PDF text extraction failed')
    text=result.stdout
   else:
    page=raw.decode('utf-8',errors='replace');page=re.sub(r'<(script|style)\b[^>]*>.*?</\1>',' ',page,flags=re.S|re.I)
    text=html.unescape(re.sub('<[^>]+>',' ',page));text=re.sub(r'[ \t]+',' ',text)
   (CACHE/(key+'.txt')).write_text(text)
   record['exactTopNcts']=sorted(set(re.findall(r'NCT\d{8}',text))&ids)
   record['state']='RETRIEVED_TEXT_EXACT_NCT_PRESENT_NOT_AUTOMATIC_FACT' if record['exactTopNcts'] else 'RETRIEVED_NO_EXACT_NCT_REQUIRES_CROSSWALK'
   record['sourceDate']=None # no invented publication date
  except Exception as exc:record.update(state='SOURCE_BLOCKED',blocker=str(exc))
  return record
 with concurrent.futures.ThreadPoolExecutor(6) as pool:records=list(pool.map(one,unique.items()))
 (DATA/'topOnlyDocumentCoverage20261107.json').write_text(json.dumps({'schemaVersion':1,'scope':'TOP_ONLY_DOCUMENT_RETRIEVAL_NO_AUTOMATIC_SCIENTIFIC_GRADES','records':records},indent=2)+'\n')
 print(json.dumps({'documentsAttempted':len(records),'retrieved':sum(r['state']!='SOURCE_BLOCKED' for r in records),'blocked':sum(r['state']=='SOURCE_BLOCKED' for r in records),'exactNctDocuments':sum(bool(r.get('exactTopNcts')) for r in records)}))
if __name__=='__main__':main()

"""Continue the owner-only installation with raw trial sources, never ratings.

Build a functional source-review preview. No unreviewed candidate is represented
as a completed decision. Unknown application identities are provisional targets,
not official application numbers. No writes to existing data or spreadsheets.
"""
from pathlib import Path
from datetime import datetime,timezone
from collections import defaultdict
import json,hashlib,gzip
ROOT=Path(__file__).resolve().parents[1];REPORT=ROOT/'reports/deep-medical-intelligence'
def read(p):return json.loads(p.read_text()) if p.exists() else json.loads(gzip.decompress(p.with_suffix(p.suffix+'.gz').read_bytes()))
def write(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n')
def build():
 now=datetime.now(timezone.utc).isoformat();inventory=read(REPORT/'inventory.json');focus=read(ROOT/'new-platform/frontend/data/p3PostDataActive.json')['records'];focus_ids={r['nct']for r in focus};trials={}
 analysis=REPORT/'trial-analysis.jsonl'
 for line in (analysis.open() if analysis.exists() else gzip.open(str(analysis)+'.gz','rt')):
  r=json.loads(line)
  if r['nctId']in focus_ids:trials[r['nctId']]=r
 sources=[];groups=defaultdict(list)
 for row in focus:
  n=row['nct'];t=trials[n];doc=t.get('registryDocument')or{};p=doc.get('protocolSection',{});arms=p.get('armsInterventionsModule',{});experimental=[a for a in arms.get('armGroups',[])if a.get('type')=='EXPERIMENTAL'];names=list(dict.fromkeys(x for a in experimental for x in a.get('interventionNames',[])))
  drug='; '.join(names)or t.get('drug')or'Registered intervention identity requires review';indication='; '.join(p.get('conditionsModule',{}).get('conditions',[]))or t['indication'];sponsor=p.get('sponsorCollaboratorsModule',{}).get('leadSponsor',{}).get('name')or row['company'];sid='registry-'+n
  src={'id':sid,'url':'https://clinicaltrials.gov/study/'+n,'title':'Official trial registry '+n,'sourceDate':p.get('statusModule',{}).get('lastUpdatePostDateStruct',{}).get('date'),'retrievedAt':(t.get('sourceProvenance')or{}).get('lastSuccessfulRemoteRetrievalAt')or now,'locator':'ClinicalTrials.gov API v2 protocolSection/resultsSection','observation':json.dumps({'title':p.get('identificationModule',{}).get('briefTitle'),'protocolId':p.get('identificationModule',{}).get('orgStudyIdInfo'),'phase':t['phase'],'status':t['status'],'primaryOutcomes':p.get('outcomesModule',{}).get('primaryOutcomes'),'resultsPosted':bool(doc.get('resultsSection'))},ensure_ascii=False),'status':'EXACT_NCT_SOURCE_CAPTURED_NOT_MEDICALLY_ADJUDICATED','evidenceType':'OFFICIAL_REGISTRY','reliability':'PRIMARY_REGISTRY_SELF_REPORTED_STUDY_DATA','identifiers':[n],'kind':'FACT'};sources.append(src)
  # Shared registered asset/condition/sponsor is only a provisional program link.
  key=(drug.casefold(),indication.casefold(),sponsor.casefold());groups[key].append((row,t,src,drug,indication))
 apps=[]
 for key,items in sorted(groups.items()):
  row,t,src,drug,indication=items[0];ncts=[x[0]['nct']for x in items];ss=[x[2]for x in items];ids=[s['id']for s in ss];app_id='provisional-'+hashlib.sha256('|'.join(key).encode()).hexdigest()[:16]
  decision={'leading':'Indeterminate','confidence':'Low','rationale':'Exact trial sources are captured. Current application identity, proposed label, all relevant evidence, and owner critical review have not been completed; no outcome is inferred from registry posting.','contraryArgument':'A sponsor may have supplied stronger or weaker evidence, including nonpublic quality and inspection information, than the public trial record reveals.','evidenceWouldChange':'Verify the current FDA application/review cycle and source-backed efficacy, safety, quality, correspondence and opposing scientific arguments.','sourceIds':ids,'predictionTimestamp':now}
  summaries={
   'Condition Intelligence':('Registered conditions: '+indication,'Disease mechanism, natural history, endpoint acceptance and indication-specific failure history require source review.'),
   'Drug Mechanism':('Registered experimental interventions: '+drug,'Target engagement and class-specific risks require original pharmacology evidence.'),
   'Clinical Trials':('Relevant exact trial identifiers: '+', '.join(ncts),'Program grouping is provisional and must be confirmed against application-level regulatory documents.'),
   'Statistics':('Registered design: '+json.dumps((t.get('registeredDesign')or{}),ensure_ascii=False)[:1800],'Plans, achieved effects, confidence intervals, multiplicity and sensitivity results need scientific adjudication.'),
   'Safety':('Official safety source '+('is posted.'if(t.get('rawResults')or{}).get('adverseEventsModule')else'is not posted in this captured registry packet.'),'Absence of registry safety results is not evidence of absent adverse events or an FDA deficiency.'),
   'Competitive Treatments':('Comparator arms: '+json.dumps(t.get('registeredArms')or{},ensure_ascii=False)[:1800],'Registered controls do not establish the complete approved standard of care or superiority.'),
   'FDA Precedents':('No precedent comparison adjudicated for this provisional application target.','Similar mechanisms do not imply identical regulatory outcomes.'),
   'Manufacturing and Inspections':('Current manufacturing/inspection acceptability remains uncertain in the owner research packet.','Unknown or nonpublic information is a gap, not evidence of a manufacturing failure.'),
   'Regulatory History':('FOCUS records the following FDA-path pointer: '+row['fdaStatus'],'This pointer is not owner confirmation of an application number, stage, current review cycle or PDUFA goal.'),
   'Scientific Contradictions':('Published/registry/sponsor/FDA discrepancy reconciliation is pending.','No consistency finding is asserted until the relevant original documents are compared.')}
  sections=[{'id':str(i+1),'title':name,'findings':[{'text':text,'status':'SOURCE_CAPTURED_NEEDS_REVIEW','kind':'FACT'if i in [0,1,2,3,4,5,8]else'HYPOTHESIS','sourceIds':ids,'limitations':limit}]}for i,(name,(text,limit))in enumerate(summaries.items())]
  apps.append({'id':app_id,'applicationNumber':None,'applicationType':'NOT_VERIFIED','reviewCycle':'NOT_VERIFIED','company':row['company'],'ticker':row['ticker'],'drug':drug,'indication':indication,'nctIds':ncts,'pdufa':{'date':None,'status':'SOURCE_POINTER_REQUIRES_CURRENT_CYCLE_VERIFICATION','sourceIds':ids},'progress':{'stage':'EXACT_TRIAL_SOURCE_INGESTION','status':'MEDICAL_AND_APPLICATION_REVIEW_INCOMPLETE'},'outcome':decision,'timing':{**decision,'rationale':'No current application-specific goal date or amendment history has been cross-checked by the owner, so a by-goal decision, formal extension or missed goal cannot be distinguished.'},'blockers':[],'sections':sections,'failureRisks':[],'arguments':{k:[{'text':'Original evidence review required before a defensible '+k+' argument can be completed.','sourceIds':ids}]for k in ['approval','crl','delay']},'sources':ss,'ownerCriticalReview':{'status':'OWNER_NOT_REVIEWED','notes':'The owner may critically evaluate contrary evidence without any external reviewer or independent signoff.'},'gaps':[v[1]for v in summaries.values()]})
 levels=['Identity and application relationships','Phase-appropriate source ingestion','Disease and natural-history dossiers','Trial design and protocol investigation','Efficacy and clinical relevance','Statistical robustness','Safety and exposure','Trial integrity and evidence consistency','Competitive medical context','Application quality, inspections and regulatory risks','Historical precedents and owner critical appraisal','Separate outcome/timing decisions and immutable validation']
 progress=[{'level':i+1,'name':name,'state':'FUNCTIONAL_SOURCE_INGESTION'if i<2 else'ENGINEERING_OR_EVIDENCE_INCOMPLETE','evidence':'Exact-source inventory and resumable collector implemented; existing completed installation task IDs are unchanged.'if i<2 else'No completion claimed from source capture or a build.'}for i,name in enumerate(levels)]
 counts=inventory['counts'];packet={'schemaVersion':1,'asOf':now[:10],'generatedAt':now,'inventory':{'poolTrials':counts['poolUniqueNcts'],'focusTrials':len(focus),'applications':len(apps),'metadataScreenedTrials':counts['uniqueInventoryNcts'],'sourceExtractedTrials':counts['rawRegistryPacketsCaptured'],'fullyReviewedTrials':0,'incompleteTrials':counts['uniqueInventoryNcts'],'completedDecisions':0,'unresolvedBlockers':0,'sourceDocuments':len(sources)},'applications':apps,'sources':sources,'conditions':[],'precedents':[],'installationLevels':progress,'limitations':['Provisional program targets are not verified marketing applications; no FDA application is inferred solely from company or drug matching.','Every inventory trial was metadata screened; none is certified as fully medically investigated by this source-only installation step.','Zero identified blockers does not mean no blockers exist: application-level original-source investigation remains incomplete.','No numerical approval probabilities, composite ratings, or active legacy scoring dependencies are present.','POOL and FOCUS source data and all completed installation acceptance records are unchanged.']}
 write(ROOT/'new-platform/frontend/data/deepMedicalIntelligencePreview.json',packet);write(REPORT/'installation-continuation.json',{'asOf':now,'levels':progress,'preservesCompletedInstallation':True,'sourceOnlyPreview':True,'outcomeDecisionsCompleted':0,'applicationIdentityReviewRequired':len(apps)})
 for name in ['prediction-history.json','outcome-history.json']:
  if not(REPORT/name).exists():write(REPORT/name,{'schemaVersion':1,'records':[],'note':'No historical predictions synthesized from later outcomes.'})
 print(json.dumps(packet['inventory']))
if __name__=='__main__':build()

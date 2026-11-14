#!/usr/bin/env python3
"""Current FOCUS public-source acquisition and preliminary worksheets, never signoff.

Only exact ClinicalTrials.gov v2 registry URLs are fetched. Raw public originals
stay outside Git; generated extracts exclude contact/person-level fields. Sources
are untrusted data, never instructions. No active prediction/history is consumed.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, date
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
ROSTER = ROOT / 'new-platform/frontend/data/p3PostDataActive.json'
APPLICATIONS = ROOT / 'new-platform/backend/app/data/focus_application_snapshot.json'
MAX_BYTES = 4 * 1024 * 1024
STATES = ('DISCOVERED','RETRIEVED','HASH_CHECKED','UNREVIEWED','MISSING',
          'NOT_YET_EXPECTED','NOT_PUBLICLY_AVAILABLE','CONTRADICTORY',
          'PROVENANCE_INDEPENDENTLY_AUTHENTICATED','SCIENTIFICALLY_REVIEWED')
PHASES = {'EARLY_PHASE1','PHASE1','PHASE2','PHASE3','PHASE4','NA'}
QUESTIONS = {
 1: ('Does the original document identify this exact NCT and permitted source?',
     'Who independently checked ownership, versions, amendments, dates and cutoff?'),
 2: ('Are trial phase/status, indication and population current and cross-source consistent?',
     'Is any application cycle independently verified rather than provisionally mapped?'),
 3: ('What efficacy/safety observations are supported by original phase-appropriate results?',
     'Are effect sizes, uncertainty, analysis population and clinical limitations reconciled?'),
 4: ('Are allocation, masking, controls, eligibility and execution appropriate to the population?',
     'Do original protocols/amendments and actual conduct agree with registration?'),
 5: ('Were estimands, analysis populations, missing data and sensitivity analyses prespecified?',
     'What original SAP supports uncertainty, significance and phase-appropriate multiplicity handling?'),
 6: ('Do endpoints measure meaningful benefit for this disease and patient population?',
     'What disease standards, comparator evidence and specialist review support medical importance?'),
}
REQUESTS = {
 1: ('original_source_ownership_and_identity','independent_original_byte_and_version_attestation'),
 2: ('current_registry_and_indication_reconciliation','verified_application_identity_if_claimed'),
 3: ('original_current_phase_results_and_safety','effect_estimates_and_uncertainty_review'),
 4: ('original_protocol_and_amendments','population_controls_execution_reconciliation'),
 5: ('original_SAP_if_public','statistical_methods_uncertainty_and_missing_data_review'),
 6: ('disease_specific_endpoint_standards','independent_specialist_benefit_and_limitations_review'),
}


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name+'.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def text(value, limit=2000):
    return value[:limit] if isinstance(value,str) else None


def nct_check(nct):
    if not isinstance(nct,str) or not re.fullmatch(r'NCT[0-9]{8}',nct):
        raise ValueError('Exact NCT required')


def registry_url(nct):
    nct_check(nct)
    return 'https://clinicaltrials.gov/api/v2/studies/'+nct


def primary_results(packet):
    """Quote original aggregate primary outcome fields, never calculate efficacy.

    Original group IDs/populations/units remain intact. No p-value threshold,
    effect transformation, significance label, success decision or probability.
    """
    result_section=packet.get('resultsSection',{})
    measures=result_section.get('outcomeMeasuresModule',{}).get('outcomeMeasures',[]) if isinstance(result_section,dict) else []
    findings=[];unresolved=False
    if not isinstance(measures,list):return [],True
    for index,item in enumerate(measures[:30]):
        if not isinstance(item,dict) or item.get('type')!='PRIMARY':continue
        groups=item.get('groups',[])
        ids={g.get('id') for g in groups if isinstance(g,dict) and isinstance(g.get('id'),str)} if isinstance(groups,list) else set()
        classes=item.get('classes',[])
        analyses=item.get('analyses',[])
        references=[]
        for analysis in analyses if isinstance(analyses,list) else []:
            if isinstance(analysis,dict):references.extend(analysis.get('groupIds',[]))
        for cls in classes if isinstance(classes,list) else []:
            if not isinstance(cls,dict):continue
            for category in cls.get('categories',[]):
                if not isinstance(category,dict):continue
                references.extend(v.get('groupId') for v in category.get('measurements',[]) if isinstance(v,dict))
        if any(not isinstance(v,str) or v not in ids for v in references):unresolved=True
        # All copied fields are public aggregate outcome tables, not participant
        # contact records. Entire packet is already bounded by MAX_BYTES.
        allowed=('type','title','description','timeFrame','populationDescription','units',
                 'paramType','dispersionType','groups','denoms','classes','analyses')
        findings.append({'locator':f'resultsSection.outcomeMeasuresModule.outcomeMeasures[{index}]',
                         'reportedFields':{key:item[key] for key in allowed if key in item},
                         'groupIdentityStatus':'UNRESOLVED_RECONCILIATION_REQUIRED' if any(not isinstance(v,str) or v not in ids for v in references) else 'IDS_PRESENT_NOT_SCIENTIFICALLY_VERIFIED'})
        if len(findings)>=6:break
    return findings,unresolved


def extract(raw, nct, retrieved_at, cutoff):
    nct_check(nct)
    if not isinstance(raw,bytes) or not 1 <= len(raw) <= MAX_BYTES:
        raise ValueError('Bounded original registry bytes required')
    retrieved = datetime.fromisoformat(retrieved_at.replace('Z','+00:00'))
    if retrieved.tzinfo is None or retrieved.astimezone(timezone.utc).date()>date.fromisoformat(cutoff):
        raise ValueError('Retrieval exceeds evidence cutoff or lacks timezone')
    packet=json.loads(raw)
    if not isinstance(packet,dict): raise ValueError('Original registry packet required')
    protocol=packet.get('protocolSection',{})
    if protocol.get('identificationModule',{}).get('nctId') != nct:
        raise ValueError('Cross-trial registry packet rejected')
    status=protocol.get('statusModule',{})
    updated=status.get('lastUpdatePostDateStruct',{}).get('date')
    if updated is not None and date.fromisoformat(updated)>date.fromisoformat(cutoff):
        raise ValueError('Original source version is beyond evidence cutoff')
    captured=load('level4_registry_extraction').extract(packet,nct,raw)
    design=protocol.get('designModule',{})
    phases=design.get('phases')
    if not isinstance(phases,list) or not phases or any(not isinstance(p,str) or p not in PHASES for p in phases):
        phases=[]
    primary=protocol.get('outcomesModule',{}).get('primaryOutcomes',[])
    endpoints=[{'measure':text(e.get('measure')), 'timeFrame':text(e.get('timeFrame'),500)}
               for e in primary[:10] if isinstance(e,dict)] if isinstance(primary,list) else []
    result_section=packet.get('resultsSection')
    actual_results=isinstance(result_section,dict) and bool(result_section)
    conflict = packet.get('hasResults') is True and not actual_results
    result_quotes,unresolved_groups=primary_results(packet)
    leads=[]
    docs=packet.get('documentSection',{}).get('largeDocumentModule',{}).get('largeDocs',[])
    for doc in docs if isinstance(docs,list) else []:
        if not isinstance(doc,dict) or not (doc.get('hasProtocol') is True or doc.get('hasSap') is True): continue
        filename=doc.get('filename')
        if not isinstance(filename,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\.pdf',filename): continue
        leads.append({'sourceKind':'PROTOCOL_AND_SAP' if doc.get('hasProtocol') and doc.get('hasSap') else
                      'PROTOCOL' if doc.get('hasProtocol') else 'STATISTICAL_ANALYSIS_PLAN',
                      'url':f'https://cdn.clinicaltrials.gov/large-docs/{nct[-2:]}/{nct}/{filename}',
                      'registryDeclaredDocumentDateUnreviewed':text(doc.get('date'),30),
                      'labelUnreviewed':text(doc.get('label')), 'state':'DISCOVERED',
                      'retrieved':False,'provenanceIndependentlyAuthenticated':False})
    for ref in protocol.get('referencesModule',{}).get('references',[]):
        if not isinstance(ref,dict): continue
        pmid=ref.get('pmid')
        if isinstance(pmid,str) and re.fullmatch(r'[0-9]{1,12}',pmid):
            leads.append({'sourceKind':'PUBLICATION_REFERENCE','url':f'https://pubmed.ncbi.nlm.nih.gov/{pmid}/',
                          'citationUnreviewed':text(ref.get('citation')),'relationshipUnreviewed':text(ref.get('type')),
                          'state':'DISCOVERED','retrieved':False,'provenanceIndependentlyAuthenticated':False})
    return {'nct':nct,'sourceUrl':registry_url(nct),'studyUrl':f'https://clinicaltrials.gov/study/{nct}',
            'documentSha256':hashlib.sha256(raw).hexdigest(),'byteCount':len(raw),
            'retrievedAt':retrieved_at,'evidenceCutoffDate':cutoff,'registryPostedVersionDateUnreviewed':updated,
            'documentVersionStatus':'REGISTRY_POSTED_DATE_NOT_PROTOCOL_VERSION','protocolVersion':None,
            'state':'HASH_CHECKED','provenanceIndependentlyAuthenticated':False,'independentlyScientificallyReviewed':False,
            'phasesUnreviewed':phases,'studyStatusUnreviewed':text(status.get('overallStatus'),100),
            'indicationsUnreviewed': [text(v) for v in protocol.get('conditionsModule',{}).get('conditions',[]) if isinstance(v,str)],
            'populationUnreviewed':text(protocol.get('eligibilityModule',{}).get('eligibilityCriteria')),
            'designUnreviewed':{'allocation':text(design.get('designInfo',{}).get('allocation'),100),
                'masking':text(design.get('designInfo',{}).get('maskingInfo',{}).get('masking'),100),
                'enrollment':design.get('enrollmentInfo',{}).get('count'),
                'enrollmentType':text(design.get('enrollmentInfo',{}).get('type'),100)},
            'primaryEndpointsUnreviewed':endpoints,'registryResultsContentPresent':actual_results,
            'primaryResultsUnreviewed':result_quotes,
            'contradictionLeads':(['REGISTRY_RESULTS_FLAG_WITHOUT_RESULTS_CONTENT'] if conflict else []) +
                (['RESULT_GROUP_ID_RECONCILIATION_REQUIRED'] if unresolved_groups else []),
            'sourceLeads':leads,'capturedRegistry':captured}


def _observations(source,level):
    if source is None:return []
    field='protocolSection.'
    entries={
      1: [('Exact NCT is present in the retrieved registry packet',field+'identificationModule.nctId',source['nct'])],
      2: [('Registry-listed phases, not independently verified',field+'designModule.phases',source['phasesUnreviewed']),
          ('Registry-listed status, not independently verified',field+'statusModule.overallStatus',source['studyStatusUnreviewed'])],
      3: [('Structured registry results content is present' if source['registryResultsContentPresent'] else
           'No structured results content in this retrieved registry packet; other results sources not adjudicated',
           'resultsSection',source['registryResultsContentPresent'])],
      4: [('Registry design observation, not execution verification',field+'designModule',source['designUnreviewed'])],
      5: [('Statistical efficacy/significance/multiplicity conclusions abstained; original SAP and analyses require review',
            'documentSection.largeDocumentModule.largeDocs',None)],
      6: [('Registered primary endpoint descriptions, not a clinical relevance judgment',field+'outcomesModule.primaryOutcomes',source['primaryEndpointsUnreviewed'])],
    }[level]
    observations=[{'finding':statement,'sourceValue':value,'locator':locator,'sourceUrl':source['sourceUrl'],
             'documentSha256':source['documentSha256'],'reasons':['Direct extraction from the exact-NCT original registry packet'],
             'status':'PRELIMINARY_RESEARCH_UNREVIEWED'} for statement,locator,value in entries]
    if level in (3,5):
        for quote in source.get('primaryResultsUnreviewed',[]):
            observations.append({'finding':'Registry-reported primary outcome/analysis fields quoted without efficacy, significance or clinical-importance judgment',
                'sourceValue':quote['reportedFields'],'locator':quote['locator'],'sourceUrl':source['sourceUrl'],
                'documentSha256':source['documentSha256'],'reasons':['Literal original aggregate result fields; group IDs, units and population labels are not transformed',quote['groupIdentityStatus']],
                'status':'PRELIMINARY_RESEARCH_UNREVIEWED'})
    return observations


def worksheets(source):
    phases=source['phasesUnreviewed'] if source else []
    early=bool(phases) and set(phases)<={'EARLY_PHASE1','PHASE1','PHASE2'}
    result=[]
    for level in range(1,7):
        requests=[{'requirement':key,'state':'MISSING','meaning':'Not collected/reviewed; public availability not determined'} for key in REQUESTS[level]]
        if level in (3,5) and early:
            requests.append({'requirement':'future_phase3_confirmatory_package','state':'NOT_YET_EXPECTED',
                             'meaning':'Do not impose future Phase 3 data/SAP on an earlier-phase trial'})
        result.append({'level':level,'questions':list(QUESTIONS[level]),'phaseBasisUnreviewed':phases,
            'requiredEvidence':requests,'preliminaryFindings':_observations(source,level),
            'contradictoryFindings':source['contradictionLeads'] if source else [],
            'contradictionReviewStatus':'NOT_INDEPENDENTLY_REVIEWED',
            'limitations':['Registry observations may be outdated, incomplete or inconsistent with originals',
                           'Results posting does not establish efficacy, trial success or FDA approval',
                           'Clinical/statistical/specialist interpretation and cross-source reconciliation not completed'],
            'scientificReviewRequirements':['authorized_source_verifier','independent_clinical_reviewer',
                                            'separate_independent_challenger','independent_final_administrator'],
            'abstainWhen':['phase_or_exact_identity_unresolved','original_evidence_or_versions_missing',
                           'source_conflicts_unresolved','independent_review_not_completed'],
            'independentReviewStatus':'NOT_ADJUDICATED','assessmentCompleted':False,'scientificConclusion':None,
            'score':None,'approvalProbability':None})
    return result


def build(roster,applications,acquisitions,cutoff):
    index=load('phase_first_levels_1_6')._records
    trials=index(roster,'FOCUS roster');apps=index(applications,'application crosswalk')
    if not set(apps)<=set(trials) or not set(acquisitions)<=set(trials):raise ValueError('Evidence/crosswalk outside exact FOCUS')
    rows=[];cycles=set()
    for nct,trial in trials.items():
        receipt=acquisitions.get(nct)
        if receipt is not None:
            if (receipt.get('nct')!=nct or receipt.get('sourceUrl')!=registry_url(nct)
                    or receipt.get('evidenceCutoffDate')!=cutoff or receipt.get('state')!='HASH_CHECKED'
                    or receipt.get('provenanceIndependentlyAuthenticated') is not False
                    or receipt.get('independentlyScientificallyReviewed') is not False
                    or not isinstance(receipt.get('documentSha256'),str)
                    or not re.fullmatch(r'[0-9a-f]{64}',receipt['documentSha256'])
                    or receipt.get('capturedRegistry',{}).get('sha256')!=receipt['documentSha256']
                    or receipt.get('capturedRegistry',{}).get('nct')!=nct):
                raise ValueError('Untrusted source identity, cutoff or certification')
        candidates=apps.get(nct,{}).get('candidateApplications',[])
        ids=[]
        for candidate in candidates:
            if candidate.get('ticker')!=trial['ticker']:raise ValueError('Application company mismatch')
            ids.append(candidate['cycleId']);cycles.add(candidate['cycleId'])
        rows.append({'nct':nct,'company':trial['company'],'ticker':trial['ticker'],
            'candidateApplicationCycleIdsUnverified':ids,'mappingStatus':'PROVISIONAL_NOT_VERIFIED' if ids else 'NOT_MAPPED_APPLICATION_CYCLE',
            'registrySource':receipt,'sourceCollectionStatus':'HASH_CHECKED_UNREVIEWED' if receipt else 'MISSING',
            'sourceDiscoveryPlan':[
                {'priority':1,'sourceKind':'REGISTRY','url':registry_url(nct),'state':'HASH_CHECKED' if receipt else 'DISCOVERED'},
                {'priority':2,'sourceKind':'FDA_PUBLIC_RECORD_DISCOVERY_PORTAL','url':'https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm',
                 'state':'DISCOVERED','limitation':'Portal is not trial/application evidence; exact relationship must be verified'},
                {'priority':3,'sourceKind':'SPONSOR_DISCLOSURE_LEAD','url':trial.get('regulatoryUrl'),
                 'state':'DISCOVERED','limitation':'Roster URL is an unreviewed lead; ownership/trial applicability not authenticated'},
            ]+ (receipt['sourceLeads'] if receipt else []),
            'levels':worksheets(receipt),'actualAuthenticatedSources':0,'actualIndependentAssessments':0,
            'fdaOutcomeJudgment':None,'fdaTimingJudgment':None})
    return {'schemaVersion':1,'kind':'FOCUS_LEVEL16_PRELIMINARY_RESEARCH','status':'UNREVIEWED_CURRENT_SOURCE_RESEARCH_ONLY',
        'evidenceCutoffDate':cutoff,'focusTrialCount':len(rows),'mappedTrialCount':len(apps),
        'provisionalApplicationCycleCount':len(cycles),'unmappedTrialCount':len(rows)-len(apps),
        'trialsWithRetrievedRegistry':sum(r['registrySource'] is not None for r in rows),
        'trialsWithPreliminaryResearchFindings':sum(any(l['preliminaryFindings'] for l in r['levels']) for r in rows),
        'actualAuthenticatedSources':0,'actualIndependentAssessments':0,
        'prospectiveBlindAssessment':False,'historicalPredictionInputPermitted':False,
        'sourceStates':list(STATES),'trials':rows}


def validate_snapshot(report,expected_ncts):
    if (not isinstance(report,dict) or report.get('kind')!='FOCUS_LEVEL16_PRELIMINARY_RESEARCH'
            or report.get('status')!='UNREVIEWED_CURRENT_SOURCE_RESEARCH_ONLY'
            or report.get('actualAuthenticatedSources')!=0 or report.get('actualIndependentAssessments')!=0
            or report.get('prospectiveBlindAssessment') is not False
            or report.get('historicalPredictionInputPermitted') is not False):
        raise ValueError('Preliminary research cannot certify reviews, provenance or blind predictions')
    trials=load('phase_first_levels_1_6')._records({'records':report.get('trials')},'preliminary research')
    if set(trials)!=set(expected_ncts) or report.get('focusTrialCount')!=len(trials):
        raise ValueError('Research snapshot must preserve exact complete FOCUS roster')
    for nct,trial in trials.items():
        levels=trial.get('levels')
        if not isinstance(levels,list) or [v.get('level') for v in levels]!=list(range(1,7)):
            raise ValueError('All six separate preliminary worksheets required')
        if trial.get('actualAuthenticatedSources')!=0 or trial.get('actualIndependentAssessments')!=0:
            raise ValueError('Preliminary trial cannot claim independent review')
        if trial.get('fdaOutcomeJudgment') is not None or trial.get('fdaTimingJudgment') is not None:
            raise ValueError('No FDA predictions in preliminary research')
        for item in levels:
            if (item.get('independentReviewStatus')!='NOT_ADJUDICATED' or item.get('assessmentCompleted') is not False
                    or item.get('scientificConclusion') is not None or item.get('score') is not None
                    or item.get('approvalProbability') is not None
                    or any(f.get('status')!='PRELIMINARY_RESEARCH_UNREVIEWED' for f in item.get('preliminaryFindings',[]))):
                raise ValueError('Proposed research finding cannot become scientific signoff')
        receipt=trial.get('registrySource')
        if receipt:
            retrieved=datetime.fromisoformat(receipt['retrievedAt'].replace('Z','+00:00'))
            if retrieved.tzinfo is None or retrieved.astimezone(timezone.utc).date()>date.fromisoformat(report['evidenceCutoffDate']):
                raise ValueError('Saved research receipt exceeds cutoff')
            posted=receipt.get('registryPostedVersionDateUnreviewed')
            if posted is not None and date.fromisoformat(posted)>date.fromisoformat(report['evidenceCutoffDate']):
                raise ValueError('Saved registry source version exceeds cutoff')
            if (receipt.get('nct')!=nct or receipt.get('sourceUrl')!=registry_url(nct)
                    or receipt.get('evidenceCutoffDate')!=report['evidenceCutoffDate']
                    or receipt.get('provenanceIndependentlyAuthenticated') is not False
                    or receipt.get('independentlyScientificallyReviewed') is not False):
                raise ValueError('Invalid preliminary source identity/cutoff/authentication')
            allowed={(receipt['sourceUrl'],receipt['documentSha256'])}
            leads={s['url'] for s in trial['sourceDiscoveryPlan'] if s.get('url')}
            for original in trial.get('additionalOriginalDocuments',[]):
                original_retrieved=datetime.fromisoformat(original['retrievedAt'].replace('Z','+00:00'))
                if original_retrieved.tzinfo is None or original_retrieved.astimezone(timezone.utc).date()>date.fromisoformat(report['evidenceCutoffDate']):
                    raise ValueError('Saved original document receipt exceeds cutoff')
                if (original.get('nct')!=nct or original.get('sourceUrl') not in leads
                        or original.get('state')!='HASH_CHECKED' or original.get('evidenceCutoffDate')!=report['evidenceCutoffDate']
                        or original.get('provenanceIndependentlyAuthenticated') is not False
                        or original.get('independentlyScientificallyReviewed') is not False
                        or not isinstance(original.get('documentSha256'),str)
                        or not re.fullmatch(r'[0-9a-f]{64}',original['documentSha256'])):
                    raise ValueError('Invalid original document receipt, cutoff or certification')
                allowed.add((original['sourceUrl'],original['documentSha256']))
            for item in levels:
                for finding in item['preliminaryFindings']:
                    if (finding.get('sourceUrl'),finding.get('documentSha256')) not in allowed:
                        raise ValueError('Preliminary finding crossed original evidence identity')
    return trials


def readiness_report(research,roster,applications,definition):
    validate_snapshot(research,[r['nct'] for r in roster['records']])
    checkpoint={'generatedAt':research.get('generatedAt'),'results':{
        t['nct']:{'status':'CAPTURED_UNREVIEWED','evidence':t['registrySource']['capturedRegistry']}
        for t in research['trials'] if t['registrySource']}}
    return load('phase_first_levels_1_6').build(roster,applications,checkpoint,definition)


def acquire(nct,root,cutoff,opener=urllib.request.urlopen,now=None):
    root=Path(root)
    if root.is_symlink() or root.resolve().is_relative_to(ROOT):raise ValueError('Original bytes must remain outside repository')
    url=registry_url(nct)
    request=urllib.request.Request(url,headers={'User-Agent':'PDUFA-source-readiness-development/1.0','Accept':'application/json'})
    with opener(request,timeout=30) as response:
        if response.geturl()!=url:raise ValueError('Registry redirect changed original source locator')
        raw=response.read(MAX_BYTES+1)
    timestamp=(now or datetime.now(timezone.utc)).isoformat()
    result=extract(raw,nct,timestamp,cutoff)
    target=root/'registry'/nct/(result['documentSha256']+'.json')
    for path in (root,root/'registry',root/'registry'/nct,target):
        if path.is_symlink():raise ValueError('Symlinked original evidence path rejected')
    target.parent.mkdir(parents=True,exist_ok=True)
    try:
        with target.open('xb') as handle:handle.write(raw)
    except FileExistsError:
        if target.read_bytes()!=raw:raise ValueError('Existing original bytes changed; never overwrite evidence')
    if hashlib.sha256(target.read_bytes()).hexdigest()!=result['documentSha256']:
        raise ValueError('Stored original bytes differ from retrieval')
    return result


def acquire_registry_document(lead,nct,root,cutoff,opener=urllib.request.urlopen,now=None):
    nct_check(nct)
    url=lead.get('url')
    prefix=f'https://cdn.clinicaltrials.gov/large-docs/{nct[-2:]}/{nct}/'
    if (lead.get('sourceKind') not in {'PROTOCOL','STATISTICAL_ANALYSIS_PLAN','PROTOCOL_AND_SAP'}
            or not isinstance(url,str) or not url.startswith(prefix)
            or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\.pdf',url[len(prefix):])):
        raise ValueError('Only exact-NCT public registry protocol/SAP downloads are permitted')
    root=Path(root)
    if root.is_symlink() or root.resolve().is_relative_to(ROOT):raise ValueError('Original documents must remain outside Git')
    timestamp=(now or datetime.now(timezone.utc)).isoformat()
    retrieved=datetime.fromisoformat(timestamp)
    if retrieved.tzinfo is None or retrieved.astimezone(timezone.utc).date()>date.fromisoformat(cutoff):raise ValueError('Retrieval beyond cutoff')
    with opener(urllib.request.Request(url,headers={'User-Agent':'PDUFA-source-readiness-development/1.0'}),timeout=30) as response:
        if response.geturl()!=url:raise ValueError('Unexpected document redirect')
        raw=response.read(16*1024*1024+1)
    if not raw.startswith(b'%PDF-') or len(raw)>16*1024*1024:raise ValueError('Bounded original public PDF required')
    digest=hashlib.sha256(raw).hexdigest()
    target=root/'documents'/nct/(digest+'.pdf')
    for path in (root,root/'documents',root/'documents'/nct,target):
        if path.is_symlink():raise ValueError('Symlinked original document rejected')
    target.parent.mkdir(parents=True,exist_ok=True)
    try:
        with target.open('xb') as handle:handle.write(raw)
    except FileExistsError:
        if target.read_bytes()!=raw:raise ValueError('Refusing changed original document bytes')
    if hashlib.sha256(target.read_bytes()).hexdigest()!=digest:raise ValueError('Stored document integrity mismatch')
    return {'nct':nct,'sourceUrl':url,'sourceKind':lead['sourceKind'],'documentSha256':digest,
            'byteCount':len(raw),'retrievedAt':timestamp,'evidenceCutoffDate':cutoff,'state':'HASH_CHECKED',
            'registryDeclaredDocumentDateUnreviewed':lead.get('registryDeclaredDocumentDateUnreviewed'),
            'publicationDate':None,'documentVersion':None,'protocolVersion':None,
            'exactIdentityReviewStatus':'PENDING_ORIGINAL_DOCUMENT_REVIEW',
            'provenanceIndependentlyAuthenticated':False,'independentlyScientificallyReviewed':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--cutoff',default=datetime.now(timezone.utc).date().isoformat())
    args=parser.parse_args()
    roster=json.loads(ROSTER.read_text(encoding='utf-8'));apps=json.loads(APPLICATIONS.read_text(encoding='utf-8'))
    acquisitions={};failures=[]
    def fetch(trial):
        try:return trial['nct'],acquire(trial['nct'],args.evidence_root,args.cutoff),None
        except Exception as exc:return trial['nct'],None,type(exc).__name__
    with ThreadPoolExecutor(max_workers=3) as pool:
        for nct,receipt,error in pool.map(fetch,roster['records']):
            if receipt:acquisitions[nct]=receipt
            else:failures.append({'nct':nct,'status':'RETRIEVAL_FAILED_RETRY_REQUIRED','errorClass':error})
    report=build(roster,apps,acquisitions,args.cutoff)
    report['retrievalFailures']=failures;report['generatedAt']=datetime.now(timezone.utc).isoformat()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    if args.output.exists():raise ValueError('Refusing to overwrite an existing research snapshot')
    args.output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('focusTrialCount','trialsWithRetrievedRegistry','trialsWithPreliminaryResearchFindings','actualAuthenticatedSources','actualIndependentAssessments')}))


if __name__=='__main__':main()

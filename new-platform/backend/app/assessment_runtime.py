"""Owner-triggered, exact-NCT, versioned evidence assessments.

Six independent evidence engines. Coverage indices are reproducible checklist
measurements, never efficacy ratings, approval probabilities or calibration.
Historical execution reads only original snapshots captured before its cutoff.
"""
from __future__ import annotations

from datetime import date, datetime, timezone, timedelta
import hashlib
import io
import json
import math
import re
from uuid import uuid4
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, StrictInt
from sqlalchemy import text

VERSION = 'assessment-evidence-v2.0.1'
NCT = re.compile(r'^NCT\d{8}$')
PHASES = {'EARLY_PHASE1', 'PHASE1', 'PHASE2', 'PHASE3', 'PHASE4', 'NA'}
NAMES = {1: 'Source identity and provenance', 2: 'Registry and phase verification',
         3: 'Clinical results evidence', 4: 'Trial design and protocol investigation',
         5: 'Statistical analysis and multiplicity', 6: 'Endpoint clinical relevance'}
# No application outcomes, cached forecasts, reference narratives or derived
# browse features cross this explicit scoring boundary.
PROTOCOL = {'identificationModule': ('nctId', 'briefTitle', 'officialTitle'),
            'statusModule': ('overallStatus', 'lastUpdatePostDateStruct', 'primaryCompletionDateStruct', 'completionDateStruct'),
            'sponsorCollaboratorsModule': ('leadSponsor',),
            'conditionsModule': ('conditions',),
            'designModule': ('studyType', 'phases', 'designInfo', 'enrollmentInfo'),
            'outcomesModule': ('primaryOutcomes', 'secondaryOutcomes'),
            'eligibilityModule': ('eligibilityCriteria', 'sex', 'minimumAge', 'maximumAge', 'healthyVolunteers'),
            'armsInterventionsModule': ('armGroups', 'interventions')}


def now():
    return datetime.now(timezone.utc).isoformat()


def packed(v):
    return json.dumps(v, sort_keys=True, separators=(',', ':'), allow_nan=False)


def sha(v):
    return hashlib.sha256(packed(v).encode()).hexdigest()


class RunInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    nct: str = Field(pattern=r'^NCT\d{8}$')
    level: StrictInt = Field(ge=1, le=6)
    mode: str = Field(pattern=r'^(CURRENT_EVIDENCE|BLIND_HISTORICAL)$')
    cutoffDate: date | None = None

    def checked(self):
        if self.mode == 'BLIND_HISTORICAL':
            if not self.cutoffDate or self.cutoffDate >= datetime.now(timezone.utc).date():
                raise HTTPException(422, 'Blind Historical requires a valid past cutoff date')
        elif self.cutoffDate is not None:
            raise HTTPException(422, 'Current Evidence cannot accept a historical cutoff')
        return self


def initialize(engine):
    """Additive isolated schema; no alterations to existing research tables."""
    with engine.begin() as c:
        c.execute(text('''CREATE TABLE IF NOT EXISTS assessment_v2_jobs (
            run_id TEXT PRIMARY KEY, nct_id VARCHAR(11) NOT NULL, request_json TEXT NOT NULL,
            status TEXT NOT NULL, progress_json TEXT NOT NULL, created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL, error TEXT)'''))
        c.execute(text('''CREATE TABLE IF NOT EXISTS assessment_v2_sources (
            snapshot_id TEXT PRIMARY KEY, nct_id VARCHAR(11) NOT NULL,
            captured_at TEXT NOT NULL, published_at TEXT NOT NULL, source_url TEXT NOT NULL,
            raw_sha256 TEXT NOT NULL, input_sha256 TEXT NOT NULL, document_json TEXT NOT NULL)'''))
        c.execute(text('''CREATE INDEX IF NOT EXISTS assessment_v2_source_nct
            ON assessment_v2_sources(nct_id,captured_at)'''))
        c.execute(text('''CREATE TABLE IF NOT EXISTS assessment_v2_results (
            run_id TEXT PRIMARY KEY REFERENCES assessment_v2_jobs(run_id),
            nct_id VARCHAR(11) NOT NULL, level INTEGER NOT NULL CHECK(level BETWEEN 1 AND 6),
            engine_version TEXT NOT NULL, mode TEXT NOT NULL, created_at TEXT NOT NULL,
            report_hash TEXT NOT NULL, report_json TEXT NOT NULL)'''))
        c.execute(text('CREATE INDEX IF NOT EXISTS assessment_v2_result_nct ON assessment_v2_results(nct_id,created_at)'))
        for table in ('assessment_v2_sources', 'assessment_v2_results'):
            if engine.dialect.name == 'postgresql':
                c.execute(text('''CREATE OR REPLACE FUNCTION assessment_v2_immutable() RETURNS trigger
                    LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Assessment evidence and results are append-only'; END; $$'''))
                exists = c.execute(text('SELECT 1 FROM pg_trigger WHERE tgname=:name AND tgrelid=CAST(:table AS regclass)'),
                                   {'name': table+'_immutable', 'table': table}).scalar()
                if not exists:
                    c.execute(text(f'CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON {table} FOR EACH STATEMENT EXECUTE FUNCTION assessment_v2_immutable()'))
            else:
                for operation in ('UPDATE', 'DELETE'):
                    c.execute(text(f"CREATE TRIGGER IF NOT EXISTS {table}_{operation.lower()} BEFORE {operation} ON {table} BEGIN SELECT RAISE(ABORT, 'Assessment history is append-only'); END"))


def without_answer_features(value):
    if isinstance(value, list):
        return [without_answer_features(item) for item in value]
    if isinstance(value, dict):
        return {key: without_answer_features(item) for key, item in value.items()
                if not re.search(r'fda|approval|\bcrl\b|prediction|probability|actual.?outcome|calibration|cached|derived', key, re.I)}
    return value


def sanitize(source, nct, captured_at):
    if not isinstance(source, dict) or source.get('protocolSection', {}).get('identificationModule', {}).get('nctId') != nct:
        raise ValueError('Registry exact-NCT identity mismatch')
    p = source['protocolSection']
    version = p.get('statusModule', {}).get('lastUpdatePostDateStruct', {}).get('date')
    try:
        if date.fromisoformat(version).isoformat() != version or version > captured_at[:10]:
            raise ValueError('Future source revision')
    except (ValueError, TypeError):
        raise ValueError('Registry source revision is missing or invalid') from None
    filtered = {module: {k: p.get(module, {}).get(k) for k in fields if k in p.get(module, {})}
                for module, fields in PROTOCOL.items()}
    phases = filtered['designModule'].get('phases', [])
    if not isinstance(phases, list) or any(x not in PHASES for x in phases):
        raise ValueError('Registry phase cannot be verified')
    # These original clinical observations are never sourced from an outcome cache.
    results = source.get('resultsSection', {})
    retained = {k: results[k] for k in ('participantFlowModule', 'baselineCharacteristicsModule', 'outcomeMeasuresModule', 'adverseEventsModule') if k in results}
    # Do not promote links into collected or scientifically authenticated documents.
    documents = source.get('documentSection', {}).get('largeDocumentModule', {}).get('largeDocs', [])
    docs = [{k: d.get(k) for k in ('typeAbbrev', 'hasProtocol', 'hasSap', 'date', 'uploadDate', 'filename')} for d in documents if isinstance(d, dict)]
    return without_answer_features({'protocolSection': filtered, 'resultsSection': retained, 'documents': docs})


def collect_registry(nct):
    url = 'https://clinicaltrials.gov/api/v2/studies/'+nct
    try:
        with urlopen(Request(url, headers={'Accept': 'application/json', 'User-Agent': 'PDUFA-Assessment/2'}), timeout=25) as response:
            if response.geturl() != url or 'application/json' not in response.headers.get('Content-Type', ''):
                raise ValueError('Unexpected registry source response')
            raw = response.read(4_000_001)
    except HTTPError as exc:
        raise ValueError('Registry trial not found' if exc.code == 404 else 'Registry source unavailable') from None
    if len(raw) > 4_000_000:
        raise ValueError('Registry evidence exceeds source budget')
    captured = now()
    source = sanitize(json.loads(raw), nct, captured)
    return {'snapshot_id': str(uuid4()), 'nct_id': nct, 'captured_at': captured,
            'published_at': source['protocolSection']['statusModule']['lastUpdatePostDateStruct']['date'],
            'source_url': url, 'raw_sha256': hashlib.sha256(raw).hexdigest(),
            'input_sha256': sha(source), 'document_json': packed(source)}


def collect_documents(source, level):
    """Bounded original CT.gov protocol/SAP retrieval, never a link-presence claim."""
    if level not in {4, 5}:
        return source
    doc=json.loads(source['document_json']);leads=doc.get('documents', [])
    desired=('hasProtocol',) if level==4 else ('hasSap', 'hasProtocol')
    collected=[]
    for flag in desired:
        choices=sorted([d for d in leads if d.get(flag) and isinstance(d.get('filename'),str)
                        and re.fullmatch(r'[A-Za-z0-9_]+\.pdf',d['filename'])],key=lambda d:str(d.get('uploadDate') or ''))
        if not choices:continue
        lead=choices[-1]
        url='https://cdn.clinicaltrials.gov/large-docs/'+source['nct_id'][-2:]+'/'+source['nct_id']+'/'+lead['filename']
        receipt={'kind':flag,'url':url,'registeredDocumentDate':lead.get('date'),'registeredUploadDate':lead.get('uploadDate'),
                 'verification':'UNAVAILABLE','limitations':['Only the latest linked document is collected; amendment completeness is unresolved.']}
        try:
            from pypdf import PdfReader
            with urlopen(Request(url,headers={'User-Agent':'PDUFA-Assessment/2'}),timeout=25) as response:
                if response.geturl()!=url:raise ValueError('Unexpected original document redirect')
                raw=response.read(16_000_001)
            if len(raw)>16_000_000 or not raw.startswith(b'%PDF-'):raise ValueError('Invalid or oversized PDF')
            pdf=PdfReader(io.BytesIO(raw));pages=[]
            for page in pdf.pages[:80]:
                pages.append((page.extract_text() or '')[:20000])
                if sum(map(len,pages))>250000:break
            body='\n'.join(pages)[:250000]
            receipt.update(verification='ORIGINAL_LINKED_PDF_RETRIEVED',sha256=hashlib.sha256(raw).hexdigest(),capturedAt=now(),
                           extractedPages=len(pages),totalPages=len(pdf.pages),extractedText=body)
        except Exception:
            receipt['limitations'].append('Original document could not be retrieved or parsed; no document-content inference made.')
        collected.append(receipt)
    doc['originalDocuments']=collected
    source={**source,'captured_at':now(),'document_json':packed(doc),'input_sha256':sha(doc)}
    return source


def source_for(engine, request, collector=collect_registry):
    if request.mode == 'CURRENT_EVIDENCE':
        source = collect_documents(collector(request.nct), request.level)
        if source['nct_id'] != request.nct or source['input_sha256'] != sha(json.loads(source['document_json'])):
            raise ValueError('Collected evidence identity/digest mismatch')
        with engine.begin() as c:
            c.execute(text('''INSERT INTO assessment_v2_sources
                (snapshot_id,nct_id,captured_at,published_at,source_url,raw_sha256,input_sha256,document_json)
                VALUES(:snapshot_id,:nct_id,:captured_at,:published_at,:source_url,:raw_sha256,:input_sha256,:document_json)'''), source)
        return source
    # A current-source cache is NEVER consulted. Both original capture and
    # source publication must precede the cutoff, independently of revision date.
    cutoff = request.cutoffDate.isoformat()
    with engine.connect() as c:
        rows = c.execute(text('''SELECT * FROM assessment_v2_sources WHERE nct_id=:nct
            AND captured_at<:end AND published_at<=:cutoff ORDER BY captured_at DESC'''),
            {'nct': request.nct, 'end': (request.cutoffDate+timedelta(days=1)).isoformat(), 'cutoff': cutoff}).mappings()
        for row in rows:
            doc = json.loads(row['document_json'])
            if sha(doc) != row['input_sha256'] or doc['protocolSection']['identificationModule']['nctId'] != request.nct:
                raise ValueError('Historical source integrity failure')
            return dict(row)
    raise ValueError('NO_ELIGIBLE_HISTORICAL_SNAPSHOT: no original evidence captured by this cutoff; current data cannot be backdated')


def criterion(id, present, explanation, locator, expected=True):
    return {'id': id, 'state': ('AVAILABLE' if present else 'MISSING') if expected else 'NOT_YET_EXPECTED',
            'explanation': explanation, 'locator': locator}


def clinical_context(doc):
    p = doc['protocolSection']; design = p['designModule']; status = p['statusModule']
    phases = design.get('phases', [])
    early = bool(phases) and all(x in {'EARLY_PHASE1', 'PHASE1', 'PHASE2'} for x in phases)
    conditions = p['conditionsModule'].get('conditions', [])
    label = ' '.join(conditions).lower()
    domains = [
        ('tobacco cessation', r'smoking|tobacco|nicotine', 'Sustained biochemically verified abstinence, relapse and neuropsychiatric safety; distinguish treatment duration from durable cessation.'),
        ('oncology', r'cancer|carcinoma|lymphoma|leukemia|tumou?r|myeloma|sarcoma', 'Separate survival and symptoms from response/PFS surrogates; assess line of therapy, comparator, censoring and safety exposure.'),
        ('cardiovascular', r'heart|cardio|hypertension|blood pressure', 'Distinguish clinical events and patient function from physiologic surrogates; assess baseline risk and cardiac safety.'),
        ('nephrology', r'kidney|renal|nephro', 'Distinguish kidney failure/eGFR trajectory from proteinuria surrogates; assess background therapy and electrolyte/renal safety.'),
        ('metabolic', r'diabet|obesity|weight|metabolic', 'Distinguish glycemic/weight measures from durable clinical outcomes; assess hypoglycemia and treatment withdrawal.'),
        ('respiratory', r'pulmonary|lung|asthma|copd|respirat', 'Assess exacerbations, symptoms and function alongside physiology; examine infections and background therapy.'),
        ('neurology', r'alzheimer|parkinson|dementia|neurolog|multiple sclerosis|epilep', 'Separate biomarkers from cognition/function or clinical events; assess durability, missingness and CNS harms.'),
        ('immunology', r'colitis|crohn|psoriasis|arthritis|autoimmune|inflamm', 'Assess remission, symptom/function benefit, durability and steroid sparing; examine serious infection and prior treatment.'),
        ('ophthalmology', r'retina|macular|glaucoma|vision|ocular', 'Distinguish structural biomarkers from visual function and patient-important vision; assess eye-level correlation and durability.')]
    matches = [{'domain': name, 'question': question} for name, pattern, question in domains if re.search(pattern, label)]
    return {'phases': phases, 'phaseVerification': 'OFFICIAL_REGISTRY_DECLARATION' if phases else 'UNRESOLVED',
            'registryStatus': status.get('overallStatus'), 'regulatoryStatus': 'UNVERIFIED_NO_APPLICATION_IDENTITY',
            'conditions': conditions, 'earlyPhase': early, 'pivotal': 'PHASE3' in phases,
            'resultsExpected': status.get('overallStatus') in {'COMPLETED', 'TERMINATED'},
            'indicationAnalysis': matches or [{'domain': 'unmapped indication', 'question': 'No supported disease-specific interpretation; obtain the appropriate clinical context and patient-important outcome definition.'}]}


def level_one(doc, context, source):
    p = doc['protocolSection']
    return [criterion('exact_identity', p['identificationModule'].get('nctId') == source['nct_id'], 'Official response exact NCT matches the requested trial.', 'protocolSection.identificationModule.nctId'),
            criterion('original_receipt', bool(source['raw_sha256']), 'Original response byte digest and capture timestamp retained; this is provenance, not clinical validation.', 'raw_sha256; captured_at'),
            criterion('source_revision', bool(source['published_at']), 'Official registry revision date is recorded separately from retrieval.', 'protocolSection.statusModule.lastUpdatePostDateStruct'),
            criterion('sponsor', bool(p['sponsorCollaboratorsModule'].get('leadSponsor', {}).get('name')), 'Registry-reported sponsor ownership identified.', 'protocolSection.sponsorCollaboratorsModule')], []


def level_two(doc, context, source):
    p = doc['protocolSection']
    return [criterion('phase', bool(context['phases']) and 'NA' not in context['phases'], 'Registry phase is a source declaration; NA/absent cannot establish an interventional drug phase.', 'protocolSection.designModule.phases'),
            criterion('trial_status', bool(context['registryStatus']), 'Clinical trial status is distinct from an FDA application decision.', 'protocolSection.statusModule.overallStatus'),
            criterion('indication', bool(context['conditions']), 'Use exact registered conditions rather than sponsor ticker to determine indication.', 'protocolSection.conditionsModule.conditions'),
            criterion('population', bool(p['eligibilityModule'].get('eligibilityCriteria')), 'Population inclusion/exclusion criteria are available for phase-specific review.', 'protocolSection.eligibilityModule'),
            criterion('regulatory_identity', False, 'No verified FDA application/review-cycle linkage is available; do not infer filing, approval, CRL or delay.', 'FDA application evidence unavailable')], []


def primary_results(doc):
    return [x for x in doc['resultsSection'].get('outcomeMeasuresModule', {}).get('outcomeMeasures', []) if x.get('type') == 'PRIMARY']


def level_three(doc, context, source):
    results = primary_results(doc); safety = doc['resultsSection'].get('adverseEventsModule', {})
    observations = [{'title': r.get('title'), 'timeFrame': r.get('timeFrame'), 'population': r.get('populationDescription'),
                     'groups': r.get('groups', []), 'denominators': r.get('denoms', []), 'measurements': r.get('classes', []),
                     'reportedAnalyses': r.get('analyses', [])} for r in results]
    expected = context['resultsExpected']
    quantitative = any(r.get('denoms') and any(number(m.get('value')) is not None for cl in r.get('classes',[]) for ca in cl.get('categories',[]) for m in ca.get('measurements',[])) for r in results)
    checks = [criterion('primary_results', quantitative, 'Posted quantitative primary results are distinguished from planned endpoint text; availability is not success.', 'resultsSection.outcomeMeasuresModule', expected or bool(results)),
              criterion('safety_observations', bool(safety), 'Report harms and exposure separately from efficacy; absent harms data do not establish safety.', 'resultsSection.adverseEventsModule', expected or bool(safety)),
              criterion('participant_flow', bool(doc['resultsSection'].get('participantFlowModule')), 'Participant flow supports attrition/exposure review, not proof of unbiased inference.', 'resultsSection.participantFlowModule', expected or bool(results))]
    if context['earlyPhase']:
        checks.append(criterion('future_pivotal_readout', False, 'Confirmatory Phase 3 results are not required of an earlier-phase study.', 'phase-specific applicability', False))
    return checks, observations + ([{'safety': safety}] if safety else [])


def level_four(doc, context, source):
    p=doc['protocolSection']; d=p['designModule']; info=d.get('designInfo', {}); docs=doc['documents']
    checks = [criterion('design', bool(info), 'Describe the actual design; do not treat nonrandomized or open-label design as automatically invalid.', 'protocolSection.designModule.designInfo'),
              criterion('arms', bool(p['armsInterventionsModule'].get('armGroups')), 'Identify interventions, comparator and co-interventions in the registered arms.', 'protocolSection.armsInterventionsModule'),
              criterion('enrollment', bool(d.get('enrollmentInfo', {}).get('count')), 'Registered enrollment is not a power calculation.', 'protocolSection.designModule.enrollmentInfo'),
              criterion('protocol_original', any(d['kind']=='hasProtocol' and d['verification']=='ORIGINAL_LINKED_PDF_RETRIEVED' and d.get('extractedText') for d in doc.get('originalDocuments',[])), 'Only actual retrieved original PDF content counts. Protocol amendment completeness and execution still require reconciliation.', 'originalDocuments.hasProtocol')]
    return checks, [{'design': info, 'enrollment': d.get('enrollmentInfo'), 'documentLeads': docs, 'originalProtocol': [{k:v for k,v in d.items() if k!='extractedText'} for d in doc.get('originalDocuments',[]) if d['kind']=='hasProtocol']}]


def number(value):
    try:
        x=float(value)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def level_five(doc, context, source):
    observations=[]; conflicts=[]
    for r in primary_results(doc):
        for a in r.get('analyses', []):
            low, high, estimate = (number(a.get(k)) for k in ('ciLowerLimit','ciUpperLimit','paramValue'))
            consistent = low is not None and high is not None and low <= high and (estimate is None or low <= estimate <= high)
            if (low is not None or high is not None) and not consistent:
                conflicts.append('Reported confidence interval is incomplete, reversed or excludes its point estimate: '+str(r.get('title')))
            observations.append({'endpoint': r.get('title'), 'reported': a, 'intervalCheck': 'CONSISTENT' if consistent else 'UNRESOLVED_OR_CONFLICTING',
                                 'interpretation': 'Reported analysis only. Nominal p-values do not establish family-wise significance, prespecification or clinical benefit.'})
    reported_count=len(observations)
    sap=next((d for d in doc.get('originalDocuments',[]) if d['kind']=='hasSap' and d['verification']=='ORIGINAL_LINKED_PDF_RETRIEVED'),None)
    if sap:
        body=sap.get('extractedText','')
        terms=('estimand','multiplicity','missing data','sensitivity','alpha','interim','unblind','database lock')
        excerpts={term:[body[max(0,m.start()-100):m.end()+400] for m in list(re.finditer(re.escape(term),body,re.I))[:3]] for term in terms}
        observations.append({'originalSap':{k:v for k,v in sap.items() if k!='extractedText'},'sourceExcerpts':excerpts,'interpretation':'Original text observations; keyword presence is not statistical adequacy or proof of prespecification.'})
    checks=[criterion('reported_analyses', bool(reported_count), 'Preserve reported statistical methods, effect estimates and intervals without inventing missing values.', 'resultsSection.outcomeMeasuresModule.analyses', context['resultsExpected'] or bool(reported_count)),
            criterion('sap_content', bool(sap and sap.get('extractedText')), 'Original SAP text and cited excerpts are retained where actually retrieved; statistical adequacy still requires analysis.', 'originalDocuments.hasSap', context['pivotal'] or bool(sap)),
            criterion('prespecification', False, 'SAP version/lock/unblinding chronology and multiplicity are unresolved; a posted SAP link alone cannot resolve them.', 'Original SAP/version chronology unavailable', context['pivotal'])]
    if conflicts:
        checks.append({'id':'reported_interval_consistency','state':'CONFLICTING','explanation':'; '.join(conflicts),'locator':'resultsSection.outcomeMeasuresModule.analyses'})
    return checks, observations + [{'conflicts': conflicts}]


def level_six(doc, context, source):
    endpoints = doc['protocolSection']['outcomesModule'].get('primaryOutcomes', [])
    observations=[]
    for e in endpoints:
        label = (str(e.get('measure',''))+' '+str(e.get('description',''))).lower()
        direct = bool(re.search(r'overall survival|all.cause mortality|quality of life|abstinence|hospitalization|patient.reported|symptom|pain',label))
        observations.append({'endpoint': e, 'classification': 'POTENTIALLY_PATIENT_IMPORTANT_REQUIRES_CONTEXT' if direct else 'CLINICAL_RELEVANCE_UNRESOLVED',
                             'interpretation': 'Endpoint wording alone does not verify clinical importance, meaningful magnitude or surrogate validity.'})
    return [criterion('endpoint_definition', bool(endpoints), 'Review endpoint measure, timeframe and population in the precise indication.', 'protocolSection.outcomesModule.primaryOutcomes'),
            criterion('domain_mapping', context['indicationAnalysis'][0]['domain'] != 'unmapped indication', 'Disease-specific review questions are available only for supported indication matches.', 'protocolSection.conditionsModule.conditions'),
            criterion('meaningful_effect', False, 'No sourced disease/population-specific meaningful-effect threshold is installed. Do not substitute statistical significance.', 'Clinical threshold evidence unavailable', context['resultsExpected']),
            criterion('durability_risk_benefit', False, 'Durable patient benefit and harms require original evidence beyond endpoint wording.', 'Long-term clinical evidence unavailable', context['resultsExpected'])], observations


ENGINES={1:level_one,2:level_two,3:level_three,4:level_four,5:level_five,6:level_six}


def assess(request, source):
    doc=json.loads(source['document_json']); context=clinical_context(doc)
    if sha(doc) != source['input_sha256']:
        raise ValueError('Frozen evidence input digest mismatch')
    if request.mode == 'BLIND_HISTORICAL':
        cutoff=request.cutoffDate.isoformat()
        if source['captured_at'][:10] > cutoff or source['published_at'] > cutoff:
            raise ValueError('Historical evidence leakage detected')
    checks, observations=ENGINES[request.level](doc, context, source)
    if not context['phases'] or 'NA' in context['phases']:
        # No downstream readiness conclusion can waive phase verification.
        checks.append(criterion('phase_first', False, 'Resolve clinical phase before applying phase-specific scientific requirements.', 'protocolSection.designModule.phases'))
    applicable=[c for c in checks if c['state'] != 'NOT_YET_EXPECTED']; available=sum(c['state']=='AVAILABLE' for c in applicable)
    missing=[c['explanation'] for c in checks if c['state'] in {'MISSING','CONFLICTING'}]
    return {'schemaVersion':2, 'kind':'TRIAL_LEVEL_EVIDENCE_ASSESSMENT', 'nct':request.nct, 'level':request.level,
            'name':NAMES[request.level], 'engineVersion':VERSION+f'/level-{request.level}', 'mode':request.mode,
            'cutoffDate':request.cutoffDate.isoformat() if request.cutoffDate else None, 'executedAt':now(),
            'scientificStatus':'EVIDENCE_GAPS' if missing else 'SOURCE_CHECKS_COMPLETE_NOT_CLINICAL_VALIDATION',
            'score':{'value':round(100*available/len(applicable),1) if applicable else None, 'available':available,'applicable':len(applicable),
                     'kind':'LEVEL_SPECIFIC_EVIDENCE_COVERAGE', 'method':'100 × available applicable checks / all applicable checks; not a scientific efficacy score or probability'},
            'fdaPrediction':{'outcome':'ABSTAIN','probability':None,'confidence':'UNCALIBRATED','calibration':'NO_VALIDATED_FDA_MODEL'},
            'context':context,'checks':checks,'observations':observations,'risks':missing,
            'recommendations':missing or ['Review the retained source observations; source completeness does not establish medical benefit.'],
            'limitations':['Registry evidence is sponsor-reported; official receipt does not authenticate scientific claims.',
                           'Original protocol/SAP extraction is bounded and does not prove amendment completeness or statistical adequacy. FDA review documents and clinical-meaningfulness thresholds are not installed; no validated FDA model exists.',
                           'Historical execution is algorithmically outcome-isolated; it does not prove the human owner was outcome-unexposed.'],
            'evidence':{k:source[k] for k in ('snapshot_id','nct_id','captured_at','published_at','source_url','raw_sha256','input_sha256')},
            'ownerReviewStatus':'OWNER_NOT_REVIEWED', 'activationStatus':'NOT_ACTIVE_SCIENTIFIC_GAPS',
            'historicalAccuracyEligible':False, 'savedToDatabase':True}


def progress(engine, run_id, stage):
    with engine.begin() as c:
        row=c.execute(text('SELECT progress_json FROM assessment_v2_jobs WHERE run_id=:id'),{'id':run_id}).scalar_one()
        events=json.loads(row)+[{'stage':stage,'at':now()}]
        c.execute(text("UPDATE assessment_v2_jobs SET status='RUNNING',progress_json=:events,updated_at=:at WHERE run_id=:id"),{'id':run_id,'events':packed(events),'at':now()})


def execute(engine, run_id, collector=collect_registry):
    try:
        with engine.connect() as c:
            raw=c.execute(text('SELECT request_json FROM assessment_v2_jobs WHERE run_id=:id'),{'id':run_id}).scalar_one()
        request=RunInput.model_validate_json(raw).checked()
        progress(engine,run_id,'RETRIEVING_CURRENT_SOURCES' if request.mode=='CURRENT_EVIDENCE' else 'SELECTING_PRE_CUTOFF_SNAPSHOT')
        source=source_for(engine,request,collector)
        progress(engine,run_id,f'EXECUTING_LEVEL_{request.level}')
        report=assess(request,source);report['runId']=run_id
        progress(engine,run_id,'PERSISTING_IMMUTABLE_RESULT')
        with engine.begin() as c:
            c.execute(text('''INSERT INTO assessment_v2_results(run_id,nct_id,level,engine_version,mode,created_at,report_hash,report_json)
                VALUES(:id,:nct,:level,:version,:mode,:at,:hash,:report)'''),
                {'id':run_id,'nct':request.nct,'level':request.level,'version':report['engineVersion'],'mode':request.mode,'at':report['executedAt'],'hash':sha(report),'report':packed(report)})
            c.execute(text("UPDATE assessment_v2_jobs SET status='COMPLETED',updated_at=:at WHERE run_id=:id"),{'id':run_id,'at':now()})
    except Exception as exc:
        # No upstream credential/HTTP body/SQL diagnostics reach owner responses.
        reason=str(exc) if isinstance(exc,ValueError) else 'Assessment execution or persistence failed; no completion confirmed'
        with engine.begin() as c:
            c.execute(text("UPDATE assessment_v2_jobs SET status='FAILED',error=:error,updated_at=:at WHERE run_id=:id"),{'id':run_id,'at':now(),'error':reason[:500]})


def create(engine, request):
    request.checked();initialize(engine)
    run_id=str(uuid4());at=now()
    with engine.begin() as c:
        c.execute(text('''INSERT INTO assessment_v2_jobs(run_id,nct_id,request_json,status,progress_json,created_at,updated_at)
            VALUES(:id,:nct,:request,'QUEUED',:progress,:at,:at)'''),{'id':run_id,'nct':request.nct,'request':request.model_dump_json(),'progress':packed([{'stage':'QUEUED','at':at}]),'at':at})
    return run_id


def status(engine,nct,run_id):
    if not NCT.fullmatch(nct) or not re.fullmatch(r'[a-f0-9-]{36}',run_id):
        raise HTTPException(422,'Exact NCT and run UUID required')
    with engine.connect() as c:
        row=c.execute(text('SELECT * FROM assessment_v2_jobs WHERE run_id=:id AND nct_id=:nct'),{'id':run_id,'nct':nct}).mappings().first()
        if not row: raise HTTPException(404,'Assessment run not found for this exact NCT')
        result=c.execute(text('SELECT report_json,report_hash FROM assessment_v2_results WHERE run_id=:id'),{'id':run_id}).first()
    state=row['status'];error=row['error']
    if state in {'QUEUED','RUNNING'} and datetime.fromisoformat(row['updated_at']) < datetime.now(timezone.utc)-timedelta(minutes=3):
        state='FAILED';error='Execution was interrupted. No completed result exists; start a new run.'
    return {'runId':run_id,'nct':nct,'status':state,'progress':json.loads(row['progress_json']),'error':error,
            'report':verified_report(result) if result else None}


def verified_report(row):
    report=json.loads(row[0])
    if sha(report)!=row[1]:
        raise HTTPException(503,'Saved assessment integrity check failed')
    return {**report,'reportHash':row[1]}


def history(engine,nct,level=None):
    if not NCT.fullmatch(nct) or (level is not None and not 1<=level<=6): raise HTTPException(422,'Exact NCT and level 1–6 required')
    with engine.connect() as c:
        query='SELECT report_json,report_hash FROM assessment_v2_results WHERE nct_id=:nct'
        if level is not None:query+=' AND level=:level'
        rows=c.execute(text(query+' ORDER BY created_at DESC,run_id DESC LIMIT 51'),{'nct':nct,'level':level}).all()
    runs=[];size=0
    for row in rows[:50]:
        size+=len(row[0].encode())
        if size>3_000_000:break
        runs.append(verified_report(row))
    return {'nct':nct,'runs':runs,'hasMore':len(rows)>len(runs)}


def catalog(engine, population, query):
    if population not in {'POOL', 'FOCUS', 'HISTORICAL'} or len(query)>100:
        raise HTTPException(422, 'Valid trial population and bounded search required')
    if population == 'FOCUS':
        records=json.loads((Path(__file__).parent/'data/assessment_trial_inventory.json').read_text())['records']
    elif population == 'POOL':
        from .source_workspace import workspace
        records=workspace()['pipeline']
    else:
        from .phase3_catalog import catalog as historic_catalog
        records=historic_catalog(engine,period='PREVIOUS',q=query,page_size=50)['trials']
    rows={}
    for item in records:
        candidates=[str(item.get(k) or '') for k in ('nct','nct_id','nctId','id')]
        nct=next((match.group(0) for value in candidates if (match:=re.search(r'NCT[0-9]{8}',value))),None)
        if not nct:continue
        title=str(item.get('study_title') or item.get('trial_title') or item.get('company') or item.get('drug') or '')
        ticker=str(item.get('ticker') or '')
        if query.lower() not in (' '.join([nct,title,ticker])).lower():continue
        rows[nct]={'nct':nct,'ticker':ticker,'title':title,'population':population}
    return {'population':population,'trials':list(rows.values())[:50]}


def router(engine_provider, auth, storage, writes, *, allow_local=False):
    api=APIRouter(prefix='/api/assessment-runtime',dependencies=[Depends(auth),Depends(storage)])
    def engine():
        value=engine_provider()
        if not allow_local and value.dialect.name!='postgresql':raise HTTPException(503,'Persistent PostgreSQL is required for assessments')
        return value
    @api.post('/runs',status_code=202,dependencies=[Depends(writes)])
    def start(request:RunInput, tasks:BackgroundTasks):
        db=engine();request.checked()
        if request.mode=='BLIND_HISTORICAL':
            initialize(db)
            try:source_for(db,request)
            except ValueError as exc:raise HTTPException(409,str(exc)) from None
        run_id=create(db,request);tasks.add_task(execute,db,run_id)
        return {'runId':run_id,'nct':request.nct,'status':'QUEUED'}
    @api.get('/runs/{nct}/{run_id}')
    def read(nct:str,run_id:str):return status(engine(),nct,run_id)
    @api.get('/trials')
    def choices(population:str='FOCUS',q:str=''):
        return catalog(engine(),population,q)
    @api.get('/history/{nct}')
    def read_history(nct:str,level:int|None=None):return history(engine(),nct,level)
    return api

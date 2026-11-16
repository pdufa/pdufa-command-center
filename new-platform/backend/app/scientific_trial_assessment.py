"""Executed source-bound scientific Levels 1–3, without composite/FDA scores.

Registry observations, original document statements and calculated contrasts are
separate findings. Scientific adequacy, owner acceptance and prediction-model
validation are never inferred from document presence or a nominal p-value.
"""
from datetime import date, datetime, timezone
import math
from pathlib import Path
import json
import re
from urllib.parse import urlparse
from .assessment_runtime import sha, now, clinical_context, without_answer_features

VERSION='scientific-trial-v1.0.1'
NAMES={1:'Trial verification',2:'Clinical trial design',3:'Efficacy and statistics'}
STATUSES={'NOT_YET_RECRUITING','RECRUITING','ENROLLING_BY_INVITATION','ACTIVE_NOT_RECRUITING','SUSPENDED','TERMINATED','COMPLETED','WITHDRAWN'}


def number(value):
    if isinstance(value,bool):return None
    try:
        result=float(value)
        return result if math.isfinite(result) else None
    except (ValueError,TypeError,OverflowError):return None


def instant(value):
    if not isinstance(value,str) or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])',value):raise ValueError('Source capture must be a complete timezone-aware instant')
    result=datetime.fromisoformat(value.replace('Z','+00:00'))
    return result.astimezone(timezone.utc)


def day(value):
    if not isinstance(value,str) or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}',value):raise ValueError('Source publication date is unresolved')
    return date.fromisoformat(value)


def finding(identity,state,explanation,locator,value=None,citations=None,concern=None):
    return {'id':identity,'state':state,'explanation':explanation,'locator':locator,
            'value':value,'citations':citations or [],'concern':concern}


def observed(identity,value,explanation,locator,source):
    present=value is not None and value!='' and value!=[] and value!={}
    citation={k:source[k] for k in ('source_url','published_at','captured_at','raw_sha256')}
    citation['locator']=locator
    return finding(identity,'SOURCE_VERIFIED' if present else 'MISSING',explanation,locator,value,[citation])


def document_evidence(doc,source,cutoff):
    """Only dated original PDFs bound to this exact registered trial may inform findings."""
    valid=[];rejected=[]
    ident=doc['protocolSection']['identificationModule'];study_id=ident.get('orgStudyIdInfo',{}).get('id')
    tokens=[source['nct_id']]+([study_id] if isinstance(study_id,str) and len(study_id)>=4 else [])
    leads={d.get('filename'):d for d in doc.get('documents',[]) if isinstance(d,dict)}
    for receipt in doc.get('originalDocuments',[]):
        reason=None
        try:
            parsed=urlparse(receipt.get('url',''));filename=parsed.path.split('/')[-1];lead=leads.get(filename,{})
            expected='/large-docs/'+source['nct_id'][-2:]+'/'+source['nct_id']+'/'+filename
            if parsed.scheme!='https' or parsed.netloc!='cdn.clinicaltrials.gov' or parsed.path!=expected or parsed.query or not lead.get(receipt.get('kind')):raise ValueError('Original PDF is not linked to this exact registry trial')
            if receipt.get('verification')!='ORIGINAL_LINKED_PDF_RETRIEVED':raise ValueError('Original document retrieval unavailable; a link is not reviewed content')
            if not re.fullmatch(r'[a-f0-9]{64}',receipt.get('sha256','')):raise ValueError('Original document digest missing')
            captured=instant(receipt.get('capturedAt'));published=day(receipt.get('registeredDocumentDate'))
            upload=receipt.get('registeredUploadDate')
            if not isinstance(upload,str) or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}(?::[0-9]{2})?',upload):raise ValueError('Registry document availability date is unresolved')
            uploaded=day(upload[:10])
            if not published<=uploaded<=captured.date()<=cutoff or captured>instant(source['captured_at']):raise ValueError('Document publication/upload/retrieval crosses evidence chronology or cutoff')
            body=receipt.get('extractedText','')
            if not isinstance(body,str) or not body.strip():raise ValueError('Original document text unavailable')
            header=re.sub('[^A-Z0-9]','',body[:6000].upper())
            if not any(re.sub('[^A-Z0-9]','',token.upper()) in header for token in tokens):raise ValueError('Document content identity cannot be reconciled with the exact trial/study code')
            valid.append(receipt)
        except (ValueError,TypeError,AttributeError) as exc:reason=str(exc)
        if reason:rejected.append({'source':receipt.get('url'),'state':'REJECTED_EVIDENCE','reason':reason})
    return valid,rejected


def excerpt(documents,kind,pattern):
    for document in documents:
        if document['kind']!=kind:continue
        pages=document.get('pages') or [{'page':None,'text':document.get('extractedText','')}]
        for page in pages:
            text=page.get('text','')
            match=re.search(pattern,text,re.I|re.S)
            if not match:continue
            quote=text[max(0,match.start()-180):min(len(text),match.end()+650)].strip()
            # Outcome-sensitive regulatory prose never enters scientific findings.
            if re.search(r'FDA.{0,80}(approved|approval|complete response|CRL)|actual.?FDA.?outcome',quote,re.I|re.S):continue
            return {'source_url':document['url'],'published_at':document['registeredDocumentDate'],
                    'captured_at':document['capturedAt'],'raw_sha256':document['sha256'],
                    'locator':'PDF page '+str(page.get('page') or 'unpaginated retained extraction'),
                    'excerpt':quote}
    return None


def document_finding(identity,documents,kind,pattern,explanation,expected=True):
    quote=excerpt(documents,kind,pattern)
    state='DOCUMENT_REPORTED' if quote else ('UNVERIFIED' if expected else 'NOT_YET_EXPECTED')
    return finding(identity,state,explanation if quote else explanation+' No eligible source passage establishes this criterion.',
                   quote['locator'] if quote else 'Eligible original protocol/SAP',citations=[quote] if quote else [])


def level_one(doc,context,source,documents):
    p=doc['protocolSection'];design=p['designModule'];identity=p['identificationModule'];arms=p['armsInterventionsModule']
    interventions=arms.get('interventions',[])
    drugs=[x.get('name') for x in interventions if x.get('type') in {'DRUG','BIOLOGICAL','COMBINATION_PRODUCT'} and isinstance(x.get('name'),str)]
    items=[observed('exact_nct',identity.get('nctId'),'Requested and original official-registry NCT identities match exactly.','identificationModule.nctId',source),
           observed('candidate_program',{'studyTitle':identity.get('briefTitle'),'studyCode':identity.get('orgStudyIdInfo',{}).get('id'),'interventions':drugs} if drugs else None,'Drug/program names come from this exact trial, never a ticker or PDUFA date.','armsInterventionsModule.interventions',source),
           observed('sponsor',p['sponsorCollaboratorsModule'].get('leadSponsor'),'Registry-reported sponsor; this does not independently establish a listed issuer or ticker.','sponsorCollaboratorsModule.leadSponsor',source),
           observed('phase',context['phases'] if context['phaseVerification']=='OFFICIAL_REGISTRY_DECLARATION' and 'NA' not in context['phases'] else None,'Apply the actual registered phase. Unknown/NA is not a verified clinical drug phase.','designModule.phases',source),
           observed('trial_status',context['registryStatus'] if context['registryStatus'] in STATUSES else None,'Recruitment/completion status is a clinical-trial fact, not an FDA decision.','statusModule.overallStatus',source),
           observed('indication',context['conditions'],'Only the conditions registered for this NCT determine the indication.','conditionsModule.conditions',source),
           observed('patient_population',p['eligibilityModule'],'Registered eligibility describes the target population; it is not a description of all actually enrolled participants.','eligibilityModule',source),
           observed('source_chronology',{'publishedAt':source['published_at'],'retrievedAt':source['captured_at']},'Publication/revision and retrieval are verified independently against the cutoff.','source receipt',source)]
    inventory={'registry':'VERIFIED_OFFICIAL_SOURCE','originalProtocol':'COLLECTED' if any(x['kind']=='hasProtocol' for x in documents) else 'NOT_IN_ELIGIBLE_SOURCES',
               'originalSap':'COLLECTED' if any(x['kind']=='hasSap' for x in documents) else 'NOT_IN_ELIGIBLE_SOURCES',
               'postedResults':'AVAILABLE' if doc.get('resultsSection',{}).get('outcomeMeasuresModule') else ('NOT_YET_EXPECTED' if not context['resultsExpected'] else 'NOT_IN_ELIGIBLE_SOURCES')}
    return items,[{'phaseAppropriateInventory':inventory,'publicDocumentExpectation':'Public availability is distinct from whether an internal trial protocol/SAP exists.'}]


def level_two(doc,context,source,documents):
    p=doc['protocolSection'];design=p['designModule'];info=design.get('designInfo',{});mask=info.get('maskingInfo',{})
    public_final_expected=context['resultsExpected']
    items=[observed('design_methodology',info,'Describe actual intervention model, purpose and allocation; nonrandomized designs need confounding assessment.','designModule.designInfo',source),
           observed('randomization_control',{'allocation':info.get('allocation'),'arms':p['armsInterventionsModule'].get('armGroups',[])} if info.get('allocation') else None,'Random allocation supports comparability if implemented. Registry declarations do not prove sequence concealment; comparator and co-interventions remain explicit.','designModule.designInfo; armsInterventionsModule.armGroups',source),
           observed('blinding_bias',mask if mask.get('masking') else None,'Blinding is registry-reported. Open-label designs may be appropriate but subjective outcomes and differential follow-up require bias review; masking does not prove successful blinding.','designModule.designInfo.maskingInfo',source),
           observed('population_eligibility',p['eligibilityModule'],'Inclusion/exclusion restrictions limit applicability to patients outside this registered population.','eligibilityModule',source),
           observed('sample_size',design.get('enrollmentInfo'),'Enrollment is a reported sample size, not evidence of adequate power.','designModule.enrollmentInfo',source),
           document_finding('protocol_methodology',documents,'hasProtocol',r'study\s+design|trial\s+design|randomi[sz]','Original protocol design passage; intended design is distinct from actual trial conduct.',public_final_expected),
           document_finding('allocation_concealment',documents,'hasProtocol',r'interactive\s+(?:web|voice)|IWRS|IVRS|allocation\s+conceal|randomi[sz]ation\s+(?:schedule|code|sequence)','Review sequence generation/concealment separately from the RANDOMIZED label.',public_final_expected),
           document_finding('power_rationale',documents,'hasProtocol',r'(?:sample\s+size|statistical\s+power|\bpower\b).{0,180}(?:%|percent|participants|subjects)|[0-9]{1,3}(?:\.[0-9]+)?\s*%\s*power','Reported planning assumptions/power require reconciliation with the actual endpoint, analysis family, enrollment and attrition; no observed power is fabricated.',public_final_expected),
           document_finding('protocol_amendments',documents,'hasProtocol',r'amendment|protocol\s+version|version\s+history','A version/amendment passage is reported; completeness of all amendments and implementation remains unverified.',public_final_expected)]
    concerns=[]
    if info.get('allocation') and info.get('allocation')!='RANDOMIZED':concerns.append('Nonrandom allocation leaves potential confounding; no causal efficacy conclusion from design alone.')
    if mask.get('masking')=='NONE':concerns.append('Open-label assessment may introduce performance/detection bias, especially for subjective endpoints.')
    return items,[{'designConcerns':concerns,'intendedVersusConducted':'Registry/protocol statements do not independently verify allocation concealment, adherence or outcome ascertainment.'}]


def reported_analysis(analysis):
    low,high,estimate=(number(analysis.get(k)) for k in ('ciLowerLimit','ciUpperLimit','paramValue'))
    interval='NOT_REPORTED'
    if low is not None or high is not None:interval='CONSISTENT' if low is not None and high is not None and low<=high and (estimate is None or low<=estimate<=high) else 'CONFLICTING'
    raw=analysis.get('pValue');match=re.fullmatch(r'\s*(<=|>=|<|>|≤|≥|=)?\s*([0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)\s*',str(raw or ''))
    p=number(match[2]) if match else None
    nominal='UNRESOLVED'
    if p is not None and 0<=p<=1:
        operator=match[1] or '='
        if operator in ('<','<=','≤','=') and p<.05:nominal='NOMINAL_P_BELOW_0_05_NOT_MULTIPLICITY_ADJUSTED'
        elif operator in ('>','>=','≥','=') and p>=.05:nominal='DOES_NOT_ESTABLISH_NOMINAL_P_BELOW_0_05'
    return {'reported':analysis,'intervalConsistency':interval,'nominalSignificance':nominal,
            'limitation':'Reported effect type and units are preserved. Nominal significance is not multiplicity control, clinical importance or FDA approval.'}


def endpoint_assessment(endpoint,source):
    groups={g['id']:g for g in endpoint.get('groups',[]) if isinstance(g,dict) and isinstance(g.get('id'),str)}
    controls=[key for key,g in groups.items() if re.search(r'^\s*placebo\b',g.get('title',''),re.I)]
    measurements=[m for cl in endpoint.get('classes',[]) for category in cl.get('categories',[]) for m in category.get('measurements',[])]
    values={m.get('groupId'):number(m.get('value')) for m in measurements}
    contrasts=[];unit=str(endpoint.get('unitOfMeasure',''))
    # Only a single scalar per arm and an unambiguous placebo in this endpoint.
    # Rounded percentages cannot reconstruct exact event counts or intervals.
    if len(controls)==1 and len(measurements)==len(groups) and len(values)==len(groups) and set(values)==set(groups) and re.search(r'percent|percentage|%',unit,re.I):
        control=controls[0];base=values.get(control)
        if base is not None and 0<=base<=100:
            for group,value in values.items():
                if group!=control and value is not None and 0<=value<=100:
                    contrasts.append({'method':'DIFFERENCE_OF_REPORTED_PERCENTAGES','treatmentGroup':groups[group].get('title'),
                                      'controlGroup':groups[control].get('title'),'absoluteDifferencePercentagePoints':value-base,
                                      'ratioOfReportedPercentages':value/base if base else None,'confidenceInterval':None,
                                      'limitation':'Descriptive calculation from rounded source percentages; no event counts, adjusted estimates or confidence intervals reconstructed.'})
    return {'endpointType':endpoint.get('type'),'title':endpoint.get('title'),'description':endpoint.get('description'),
            'timeFrame':endpoint.get('timeFrame'),'population':endpoint.get('populationDescription'),
            'unit':unit,'groups':list(groups.values()),'denominators':endpoint.get('denoms',[]),
            'reportedMeasurements':endpoint.get('classes',[]),'statisticalAnalyses':[reported_analysis(a) for a in endpoint.get('analyses',[])],
            'calculatedContrasts':contrasts,'citation':{'source_url':source['source_url'],'published_at':source['published_at'],
                'captured_at':source['captured_at'],'raw_sha256':source['raw_sha256'],'locator':'resultsSection.outcomeMeasuresModule: '+str(endpoint.get('title'))}}


def level_three(doc,context,source,documents):
    p=doc['protocolSection'];outcomes=doc.get('resultsSection',{}).get('outcomeMeasuresModule',{}).get('outcomeMeasures',[])
    endpoints=[endpoint_assessment(e,source) for e in outcomes if e.get('type') in {'PRIMARY','SECONDARY'}]
    primary=[e for e in endpoints if e['endpointType']=='PRIMARY'];expected=context['resultsExpected']
    items=[observed('registered_endpoints',p['outcomesModule'],'Planned primary/secondary endpoint definitions and observation windows; registration alone does not prove prespecification.','outcomesModule',source),
           finding('primary_endpoint_results','SOURCE_REPORTED' if primary else ('MISSING' if expected else 'NOT_YET_EXPECTED'),
                   'Evaluate actual posted measurements, denominators, population, effect type, intervals and nominal p-values; posting is not trial success.', 'resultsSection.outcomeMeasuresModule',value=primary),
           finding('secondary_endpoint_results','SOURCE_REPORTED' if any(e['endpointType']=='SECONDARY' for e in endpoints) else ('UNVERIFIED' if expected else 'NOT_YET_EXPECTED'),
                   'Secondary endpoints remain distinct from the primary family; exploratory analyses cannot replace a failed primary endpoint.','resultsSection.outcomeMeasuresModule',value=[e for e in endpoints if e['endpointType']=='SECONDARY']),
           document_finding('statistical_analysis_plan',documents,'hasSap',r'statistical\s+analysis\s+plan|analysis\s+population|primary\s+(?:efficacy\s+)?analysis','Original SAP passage; intended methods are not proof they were followed.',expected),
           document_finding('missing_data_handling',documents,'hasSap',r'missing.{0,100}(?:smok|imput|data|observ|assum)|(?:imput|non.?responder).{0,100}(?:missing|data)','Source-reported missing-data method; its assumptions and sensitivity to departures remain limitations.',expected),
           document_finding('multiplicity_adjustment',documents,'hasSap',r'Hochberg|Holm|Bonferroni|hierarch|gate.?keep|family.?wise|multiplicity|multiple\s+comparisons','Source-reported testing-family/procedure passage. Nominal endpoint p-values are not automatically adjusted and family/order reconciliation is still required.',expected),
           document_finding('analysis_population_estimand',documents,'hasSap',r'estimand|intent.to.treat|all\s+randomi[sz]ed|per.protocol|analysis\s+(?:population|set)','Source-reported analysis population/estimand. Do not equate a per-protocol effect with the randomized treatment-policy effect.',expected),
           document_finding('prespecification_timing',documents,'hasSap',r'database\s+lock|unblind|SAP\s+approval|prior\s+to.{0,80}(?:analysis|lock|unblind)','Document statements/dates do not establish actual lock/unblinding or reconcile earlier SAP versions. Prespecification remains UNVERIFIED.',expected)]
    for check in items:
        if check['id']=='prespecification_timing' and check['state']=='DOCUMENT_REPORTED':check['state']='UNVERIFIED'
    conflicts=[e['title'] for e in endpoints if any(a['intervalConsistency']=='CONFLICTING' for a in e['statisticalAnalyses'])]
    items.append(finding('statistical_consistency','CONCERNS' if conflicts else 'CHECKED' if endpoints else 'NOT_ASSESSED',
                         'Reported intervals are checked for ordering and point-estimate inclusion, without inventing missing uncertainty.','reported analyses',conflicts))
    label=' '.join(context['conditions']).lower()
    interpretation=('Biochemically verified smoking abstinence is a directly relevant cessation outcome. Report the measured absolute effect and its follow-up window; short-treatment abstinence is not proof of durable cessation, comparative superiority to active therapies, or overall benefit-risk.'
                    if re.search('smoking|tobacco|nicotine',label) else
                    'Clinical importance requires indication, disease severity, treatment setting, comparator and patient-important thresholds. No generic minimal clinically important difference is assigned.')
    items.append(finding('clinical_meaningfulness','SOURCE_CONTEXT_WITH_LIMITATIONS' if endpoints else 'NOT_ASSESSED',interpretation,'exact-trial indication and endpoint definitions'))
    safety=doc.get('resultsSection',{}).get('adverseEventsModule',{})
    items.append(finding('safety_benefit_risk','SOURCE_REPORTED_NOT_ADJUDICATED' if safety else ('UNVERIFIED' if expected else 'NOT_YET_EXPECTED'),
                         'Reported serious/adverse events and exposure windows must be reconciled with efficacy, ascertainment and denominators; absence of posted harms is not safety clearance.','resultsSection.adverseEventsModule',value=safety))
    items.append(finding('regulatory_application_readiness','NOT_ASSESSED',
                         'Registry design/efficacy is not an FDA application assessment. Exact drug/indication/application linkage, FDA interactions, manufacturing and labeling are unresolved; no approval forecast is generated.','Verified application dossier required'))
    flow=doc.get('resultsSection',{}).get('participantFlowModule',{})
    return items,[{'endpointEvaluations':endpoints,'participantFlow':flow,'prespecification':'UNVERIFIED',
                   'clinicalInterpretation':interpretation,'missingnessLimitation':'Outcome denominators and participant flow are reported separately; exclusions or incomplete follow-up are not silently treated as complete observations.'}]


ENGINES={1:level_one,2:level_two,3:level_three}
EXTENDED_VERSION='scientific-trial-v1.1.0'

def selected_contract(request):
    """Enforce scientific level range even for direct, non-HTTP execution."""
    if request.contract == 'SCIENTIFIC_1_3':
        if request.level not in (1,2,3):
            raise ValueError('SCIENTIFIC_1_3 supports Levels 1–3 only')
        return ENGINES,NAMES,VERSION
    if request.contract == 'SCIENTIFIC_1_6':
        if request.level not in (4,5,6):
            raise ValueError('SCIENTIFIC_1_6 supports Levels 4–6 only')
        from .scientific_levels_four_to_six import ENGINES as extended, NAMES as extended_names
        return {**ENGINES,**extended},{**NAMES,**extended_names},EXTENDED_VERSION
    raise ValueError('Unknown scientific contract')


def assess_scientific(request,source):
    raw=__import__('json').loads(source['document_json'])
    if sha(raw)!=source['input_sha256']:raise ValueError('Frozen scientific evidence digest mismatch')
    if not re.fullmatch(r'NCT[0-9]{8}',request.nct) or source['nct_id']!=request.nct or raw.get('protocolSection',{}).get('identificationModule',{}).get('nctId')!=request.nct:raise ValueError('Scientific exact-trial identity mismatch')
    if source['source_url']!='https://clinicaltrials.gov/api/v2/studies/'+request.nct:raise ValueError('Scientific source URL is not the exact official registry endpoint')
    if not re.fullmatch('[a-f0-9]{64}',source.get('raw_sha256','')):raise ValueError('Original registry response digest missing')
    captured=instant(source['captured_at']);published=day(source['published_at']);cutoff=request.cutoffDate if request.mode=='BLIND_HISTORICAL' else datetime.now(timezone.utc).date()
    if not published<=captured.date()<=cutoff:raise ValueError('Scientific historical evidence leakage or source chronology failure')
    doc=without_answer_features(raw)
    if day(doc['protocolSection']['statusModule']['lastUpdatePostDateStruct']['date']) != published:raise ValueError('Registry revision does not match its provenance receipt')
    context=clinical_context(doc)
    documents,rejected=document_evidence(doc,source,cutoff)
    engines,names,version=selected_contract(request)
    prerequisite={};selected=None;phase_ok=bool(context['phases']) and 'NA' not in context['phases'] and context['registryStatus'] in STATUSES
    for level in range(1,request.level+1):
        if level>1 and not phase_ok:
            checks=[finding('phase_first','BLOCKED_UNVERIFIED_PHASE','Resolve exact trial phase and status before scientific evaluation.','official registry')];observations=[]
        else:checks,observations=engines[level](doc,context,source,documents)
        selected={'checks':checks,'observations':observations}
        if level<request.level:prerequisite[str(level)]={'name':names[level],'engineVersion':version+'/level-'+str(level),**selected}
    checks=selected['checks'];observations=selected['observations'];gaps=[x for x in checks if x['state'] in {'MISSING','UNVERIFIED','CONCERNS','NOT_ASSESSED','BLOCKED_UNVERIFIED_PHASE'}]
    p=doc['protocolSection'];ident=p['identificationModule'];sponsor=p['sponsorCollaboratorsModule'].get('leadSponsor',{})
    risks=[x['explanation'] for x in gaps]+[x['reason'] for x in rejected]
    if request.level==3:risks+=['No independently verified prespecification/lock/unblinding reconciliation.','Nominal statistical findings do not establish multiplicity-controlled clinical benefit or FDA approval.']
    ticker=None;issuer=None;inventory_citation=None
    if request.mode=='CURRENT_EVIDENCE':
        inventory=json.loads((Path(__file__).parent/'data/assessment_trial_inventory.json').read_text(encoding='utf-8'))
        matches=[x for x in inventory['records'] if x.get('nct')==request.nct]
        if len(matches)==1:
            ticker=matches[0].get('ticker');issuer=matches[0].get('company')
            inventory_citation={'source_url':inventory['source'],'asOf':inventory['asOf'],'meaning':'Exact-NCT owner inventory label; not independent listed-issuer verification. Not used by scientific calculations.'}
    drugs=[x.get('name') for x in p['armsInterventionsModule'].get('interventions',[]) if x.get('type') in {'DRUG','BIOLOGICAL','COMBINATION_PRODUCT'} and isinstance(x.get('name'),str) and x['name'].lower()!='placebo']
    return {'schemaVersion':3,'kind':'EXECUTED_SCIENTIFIC_TRIAL_ASSESSMENT','contract':request.contract,'nct':request.nct,'level':request.level,
            'name':names[request.level],'engineVersion':version+'/level-'+str(request.level),'mode':request.mode,
            'cutoffDate':request.cutoffDate.isoformat() if request.cutoffDate else None,'executedAt':now(),
            'executionStatus':'COMPLETED_WITH_LIMITATIONS' if phase_ok else 'BLOCKED_UNVERIFIED_PHASE',
            'scientificStatus':'SOURCE_BOUND_ANALYSIS_NOT_VALIDATED','activationStatus':'RESEARCH_EXECUTION_ONLY','ownerReviewStatus':'OWNER_NOT_REVIEWED',
            'score':{'value':None,'available':0,'applicable':0,'kind':'NOT_VALIDATED','scale':None,'status':'UNSCORABLE_NO_VALIDATED_SPECIFICATION','method':'No evidence-coverage percentage, composite efficacy score or uncalibrated prediction is substituted for scientific findings.'},
            'fdaPrediction':{'outcome':'ABSTAIN','probability':None,'confidence':'NOT_VALIDATED','calibration':'NO_VALIDATED_FDA_MODEL'},
            'trialIdentity':{'nct':request.nct,'company':sponsor.get('name'),'companyMeaning':'REGISTRY_REPORTED_SPONSOR_NOT_VERIFIED_LISTED_ISSUER','ticker':ticker,'tickerStatus':'INVENTORY_REPORTED_NOT_INDEPENDENTLY_VERIFIED' if ticker else 'NOT_VERIFIED','issuerCompany':issuer,'inventoryCitation':inventory_citation,
                             'candidate':'; '.join(drugs) or ident.get('briefTitle'),'studyCode':ident.get('orgStudyIdInfo',{}).get('id'),'indication':context['conditions'],'patientPopulation':p['eligibilityModule']},
            'context':context,'checks':checks,'observations':observations,'prerequisiteAssessments':prerequisite,'rejectedEvidence':rejected,
            'documentEvidence':[{k:v for k,v in d.items() if k not in {'extractedText','pages'}} for d in documents],
            'risks':risks,'recommendations':[f"Resolve {x['id']}: {x['explanation']}" for x in gaps]+(['Reconcile complete protocol/SAP amendment chronology and actual trial conduct against reported analyses.'] if request.level>1 else []),
            'limitations':['Automatic exact-source verification is distinct from scientific validation or owner acceptance.','Original document review is bounded to retrieved, identity-matched pages; incomplete amendment history remains explicit.',
                           'No validated FDA predictive model or calibrated certainty rating is supplied.','Historical algorithmic isolation does not certify that a human researcher was outcome-unexposed.'],
            'evidence':{k:source[k] for k in ('snapshot_id','nct_id','captured_at','published_at','source_url','raw_sha256','input_sha256')},
            'historicalTarget':source.get('historicalTarget'),'historicalAccuracyEligible':False,'savedToDatabase':True}

#!/usr/bin/env python3
"""Compose ORCA-2 owner research with existing phase-first/publication checks.

Reuses the phase-first source/report boundaries. Document dates and embedded
signature claims cannot establish source authenticity or actual unblinding.
"""
from datetime import date, datetime, timezone
import importlib.util
import re
from pathlib import Path

NCT = 'NCT04576949'
GATES = ('CODE_IMPLEMENTED','TESTS_PASSED','ORIGINAL_EVIDENCE_COLLECTED','OWNER_REVIEW_COMPLETED')
CORE = {'registry','protocol-v4','sap-v1','primary-report'}


def sibling(name):
    spec=importlib.util.spec_from_file_location(name,Path(__file__).with_name(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def sap_observations(text):
    """Extract date/version claims only; never copy signer names or certificate IDs."""
    reference=re.search(r'Version\s+(\d+(?:\.\d+)*)\s*\((\w+\s+\d+,\s*\d{4})\)',text)
    signing=re.search(r'Signing Complete[^\n]*?(\d{1,2}/\d{1,2}/\d{4})',text)
    header=re.search(r'Version\s+(\d+(?:\.\d+)*)\s*[–-]\s*(\w+\s+\d+,\s*\d{4})',text)
    return {'documentVersionUnreviewed':header.group(1) if header else None,
        'documentDateUnreviewed':datetime.strptime(header.group(2),'%B %d, %Y').date().isoformat() if header else None,
        'referencedProtocolVersionUnreviewed':reference.group(1) if reference else None,
        'referencedProtocolDateUnreviewed':datetime.strptime(reference.group(2),'%B %d, %Y').date().isoformat() if reference else None,
        'embeddedSigningCompletionDateUnreviewed':datetime.strptime(signing.group(1),'%m/%d/%Y').date().isoformat() if signing else None,
        'approvalEffectiveDate':None,'authenticationStatus':'NOT_AUTHENTICATED'}


def chronology(sap,protocol_version,primary_completion,topline_publication):
    cover=sap.get('documentDateUnreviewed');signed=sap.get('embeddedSigningCompletionDateUnreviewed')
    return {'primaryCompletionDateUnreviewed':primary_completion,
        'sapCoverDateUnreviewed':cover,'embeddedSigningCompletionDateUnreviewed':signed,
        'daysCoverAfterPrimaryCompletion':(date.fromisoformat(cover)-date.fromisoformat(primary_completion)).days if cover else None,
        'embeddedSigningBeforePublicTopline':signed < topline_publication if signed else None,
        'protocolReferenceMismatch':sap.get('referencedProtocolVersionUnreviewed') != protocol_version,
        'databaseLockDate':None,'actualUnblindingDate':None,'sapApprovalEffectiveDate':None,
        'earlierStandaloneSapVersions':'UNRESOLVED','prespecificationConclusion':'UNRESOLVED',
        'postHocConclusion':None,'limitation':'Cover date, embedded completion claim, last visit and public readout are distinct events; none establishes actual database lock or unblinding.'}


def check_original_source(source,raw,document_text=None):
    """Local byte/content consistency only. Challenge pages cannot become PDFs."""
    sibling('level16_scientific_coverage').verify_receipt(source['receipt'],source['receipt']['evidenceCutoffDate'],raw)
    if source['sourceKind'] in ('PROTOCOL','STATISTICAL_ANALYSIS_PLAN','FDA_STATISTICAL_GUIDANCE') and not raw.startswith(b'%PDF-'):
        raise ValueError('Requested original PDF was not returned')
    if source['sourceKind'] in ('PROTOCOL','STATISTICAL_ANALYSIS_PLAN'):
        if not isinstance(document_text,str) or not re.search(r'\bACH-CYT-03\b',document_text):
            raise ValueError('Exact study code missing from original document extraction')
    if source['sourceKind']=='REGISTRY':
        import json
        if json.loads(raw)['protocolSection']['identificationModule']['nctId']!=NCT:
            raise ValueError('Cross-trial registry original')
    if source['sourceKind']=='PRIMARY_TRIAL_REPORT_HTML':
        text=raw.decode('utf-8')
        if NCT not in text or 'Cytisinicline for Smoking Cessation' not in text:
            raise ValueError('Primary report identity missing from original HTML')
    return 'BYTE_AND_CONTENT_CONSISTENCY_ONLY_NOT_AUTHENTICATED'


def validate_packet(packet,expected_ncts):
    if (NCT not in expected_ncts or len(set(expected_ncts))!=32
            or len(packet.get('focusNcts',[]))!=32 or set(packet['focusNcts'])!=set(expected_ncts)):
        raise ValueError('Complete current FOCUS population required')
    if (packet.get('kind')!='ORCA2_OWNER_RESEARCH_DOSSIER' or packet.get('nct')!=NCT
            or packet.get('ticker')!='ACHV' or packet.get('company')!='Achieve Life Sciences'
            or packet.get('phasesUnreviewed')!=['PHASE3']
            or packet.get('liveAccessEnabled') is not False or packet.get('ownerReviewStatus')!='OWNER_NOT_REVIEWED'
            or packet.get('externalVerificationRequired') is not False
            or packet.get('outsideReviewerCountRequired')!=0
            or packet.get('ownerCanReviewWithoutExternalVerification') is not True
            or packet.get('actualAuthenticatedSources')!=0 or packet.get('actualAdjudicatedAssessments')!=0
            or packet.get('evidenceComplete') is not False or packet.get('assessmentCompleted') is not False
            or packet.get('historicalPredictionInputPermitted') is not False
            or packet.get('prospectiveBlindAssessment') is not False
            or packet.get('approvalProbability') is not None or packet.get('scientificConclusion') is not None
            or packet.get('applicationIdentityVerified') is not False or packet.get('applicationCycleId') is not None):
        raise ValueError('Research packet cannot fabricate owner acceptance, application identity or predictions')
    import json
    policy=sibling('level1_20_owner_policy')
    policy.validate(json.loads(policy.POLICY.read_text(encoding='utf-8')))
    # Reuse the existing clinical/statistical source checks instead of a second engine.
    for name in ('level16_orca2_statistical_timeline','level16_orca2_publication_review'):
        module=sibling(name)
        module.assess(json.loads(module.INPUT.read_text(encoding='utf-8')))
    cutoff=date.fromisoformat(packet['evidenceCutoffDate']);sources={}
    for source in packet['sourceInventory']:
        key=source['id'];receipt=source['receipt']
        if key in sources or not re.fullmatch(r'[a-z0-9-]+',key):raise ValueError('Duplicate/invalid original source ID')
        if source['scope']=='TRIAL_EVIDENCE' and (source.get('nct')!=NCT or source.get('studyCode')!='ACH-CYT-03'):
            raise ValueError('Cross-trial original source contamination')
        if source['scope'] not in ('TRIAL_EVIDENCE','SPONSOR_CLAIM','CONTEXT_ONLY'):
            raise ValueError('Explicit evidence scope required')
        if source['scope']=='SPONSOR_CLAIM' and source.get('nct')!=NCT:
            raise ValueError('Sponsor claim must identify the correct trial')
        if (receipt.get('state')!='HASH_CHECKED' or receipt.get('provenanceIndependentlyAuthenticated') is not False
                or receipt.get('independentlyScientificallyReviewed') is not False
                or receipt.get('evidenceCutoffDate')!=packet['evidenceCutoffDate']
                or not re.fullmatch(r'[0-9a-f]{64}',receipt.get('documentSha256',''))
                or not receipt.get('sourceUrl','').startswith('https://')
                or source.get('authenticationStatus')!='NOT_AUTHENTICATED'):
            raise ValueError('Invalid original receipt or unsupported authentication')
        retrieved=datetime.fromisoformat(receipt['retrievedAt'].replace('Z','+00:00'))
        if retrieved.tzinfo is None or retrieved.astimezone(timezone.utc).date()>cutoff:
            raise ValueError('Retrieval outside exact UTC cutoff')
        for field in ('documentDate','publicationDate'):
            if source.get(field) and date.fromisoformat(source[field])>cutoff:
                raise ValueError('Source date exceeds cutoff')
        sources[key]=source
    if not CORE|{'sponsor-topline'}<=sources.keys():raise ValueError('Core originals and dated readout reference required')
    def citations(items):
        if not items:raise ValueError('Evidence-linked observations required')
        for item in items:
            if not item.get('sourceIds') or not set(item['sourceIds'])<=sources.keys() or not item.get('locator'):
                raise ValueError('Unbound scientific observation')
            if item.get('status')!='PRELIMINARY_UNREVIEWED':raise ValueError('Observation is not adjudication')
    for event in packet['timeline']:
        citations([event])
        if event.get('date') and date.fromisoformat(event['date'])>cutoff:raise ValueError('Timeline exceeds cutoff')
    calculated=chronology(packet['sapObservations'],sources['protocol-v4']['documentVersion'],
        packet['primaryCompletionDateUnreviewed'],sources['sponsor-topline']['publicationDate'])
    if packet['chronologyReconciliation']!=calculated:raise ValueError('Unsupported chronology resolution')
    if (packet['sapObservations']['documentVersionUnreviewed']!=sources['sap-v1']['documentVersion']
            or packet['sapObservations']['documentDateUnreviewed']!=sources['sap-v1']['documentDate']
            or packet['sapObservations'].get('authenticationStatus')!='NOT_AUTHENTICATED'
            or packet['sapObservations'].get('approvalEffectiveDate') is not None):
        raise ValueError('SAP source version mismatch')
    if [level['level'] for level in packet['levels']]!=list(range(1,7)):
        raise ValueError('Six distinct dossiers required')
    for level in packet['levels']:
        if (level['gates']!=(dict.fromkeys(GATES[:3],True)|dict.fromkeys(GATES[3:],False))
                or level.get('ownerReviewStatus')!='OWNER_NOT_REVIEWED'
                or level.get('externalReviewerRequired') is not False
                or level.get('ownerCanReviewWithoutExternalVerification') is not True
                or level.get('evidenceComplete') is not False
                or level.get('scientificConclusion') is not None
                or level.get('approvalProbability') is not None or level.get('score') is not None
                or level.get('finalReadinessClassification') not in ('READY_FOR_OWNER_RESEARCH_WITH_UNRESOLVED_EVIDENCE',)):
            raise ValueError('Owner acceptance cannot be fabricated from unreviewed research')
        citations(level['factualObservations'])
        for field in ('preliminaryInterpretation','supportingReasons','contradictoryEvidence','risksAndLimitations',
                      'missingInformation','ownerCheckQuestions','remainingEvidenceIssues'):
            if not level.get(field):raise ValueError('Incomplete research dossier')
    return sources


def prioritize_remaining(research,primary_fulltext_pmids):
    """Documentary tiers, no scientific or FDA score; preserve all 31 remaining."""
    preparation=sibling('level16_research_preparation')
    import json
    roster=json.loads(preparation.ROSTER.read_text(encoding='utf-8'))
    preparation.validate_snapshot(research,[row['nct'] for row in roster['records']])
    sibling('level16_scientific_coverage').coverage(research)
    rows=[]
    for trial in research['trials']:
        if trial['nct']==NCT:continue
        docs=trial.get('additionalOriginalDocuments',[])
        protocol=any(d['sourceKind'] in ('PROTOCOL','PROTOCOL_AND_SAP') for d in docs)
        sap=any(d['sourceKind'] in ('STATISTICAL_ANALYSIS_PLAN','PROTOCOL_AND_SAP') for d in docs)
        results=trial['registrySource']['registryResultsContentPresent']
        papers=[p for p in trial.get('publicationResearch',[]) if p['inCutoff']]
        primary=any(p['pmid'] in primary_fulltext_pmids and p.get('fullTextReceipt') for p in papers)
        core=protocol and sap and results
        tier='A_CORE_AND_PRIMARY_PUBLIC_REPORT' if core and primary else 'B_CORE_AND_INDEXED_REPORT_LEADS' if core and papers else 'C_CORE_REGISTERED_DOCUMENTS' if core else 'D_ORIGINAL_DOCUMENT_GAPS'
        rows.append({'nct':trial['nct'],'company':trial['company'],'ticker':trial['ticker'],'documentaryTier':tier,
            'protocolCollected':protocol,'sapCollected':sap,'postedRegistryResults':results,
            'primaryReportFullTextResearchClassified':primary,'indexedPublicationCount':len(papers),
            'missingOriginalDocuments':[name for name,present in [('protocol_and_amendments',protocol),('original_SAP',sap),('posted_registry_results',results),('primary_trial_report_full_text',primary)] if not present],
            'mappingStatus':trial['mappingStatus'],'clinicalContradictionsUnreviewed':trial['levels'][2]['contradictoryFindings'],
            'ownerReviewStatus':'OWNER_NOT_REVIEWED','externalVerificationRequired':False,'approvalProbability':None})
    # Within tiers use exact NCT order. No numerical weighting or efficacy ranking.
    rows.sort(key=lambda r:(r['documentaryTier'],r['nct']))
    return {'kind':'FOCUS_DOCUMENTARY_REVIEW_QUEUE_NOT_APPROVAL_RANKING','remainingTrialCount':len(rows),
        'ordering':'Documentary tiers then NCT; primary-report classification is preliminary and awaits owner source checking.',
        'nextFive':[r['nct'] for r in rows[:5]],'trials':rows}


def markdown(packet):
    validate_packet(packet,packet['focusNcts'])
    lines=['# ORCA-2 six-level research review packet','',
        'OWNER-ONLY, OUTCOME-EXPOSED RESEARCH. Owner status: OWNER_NOT_REVIEWED. No external verification required. No claim of independent certification. Live deployment remains separately controlled.', '',
        'Core originals are collected, not necessarily complete. Owner research can proceed without external signoff; scientific uncertainty and real source checks remain visible.','',
        '## Source inventory','', '| Source | Date / version (unreviewed) | Link | SHA-256 |','|---|---|---|---|']
    for source in packet['sourceInventory']:
        lines.append('| '+source['id']+' | '+str(source.get('documentDate') or source.get('publicationDate') or source.get('dateText'))+' / '+str(source.get('documentVersion'))+' | '+source['receipt']['sourceUrl']+' | '+source['receipt']['documentSha256']+' |')
    lines+=['','## Chronology','']
    for item in packet['timeline']:lines.append('- '+str(item.get('date') or 'UNRESOLVED')+': '+item['observation']+' Sources: '+', '.join(item['sourceIds'])+'; '+item['locator']+'.')
    lines+=['','Database lock, actual unblinding, effective approval date and earlier standalone SAP versions remain UNRESOLVED. Date ordering alone does not establish post-hoc analysis.','', '## Discrepancies and collection limits','']
    lines += ['- '+x for x in packet['unresolvedDiscrepancies']]
    for level in packet['levels']:
        lines+=['','## Level '+str(level['level'])+' — '+level['title'],'',level['preliminaryInterpretation'],'']
        for item in level['factualObservations']:
            lines.append('- '+item['observation']+' Sources: '+', '.join(item['sourceIds'])+'; '+item['locator']+'.')
        for label,key in [('Supporting reasons','supportingReasons'),('Contradictions/questions','contradictoryEvidence'),('Risks and limitations','risksAndLimitations'),('Missing information','missingInformation'),('Owner check questions','ownerCheckQuestions'),('Remaining evidence issues','remainingEvidenceIssues')]:
            lines+=['',label+':']+['- '+x for x in level[key]]
        lines+=['','Readiness: '+level['finalReadinessClassification']+'.','', '| Gate | Passed |','|---|---|']
        lines+=['| '+gate+' | '+str(value)+' |' for gate,value in level['gates'].items()]
    lines+=['','## Owner self-review checklist','']+['- '+x for x in packet['ownerSelfReviewChecklist']]
    lines+=['','## Original-source checks','']+['- '+x for x in packet['sourceCrossChecks']]
    return '\n'.join(lines)+'\n'

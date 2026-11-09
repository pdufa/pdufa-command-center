"""Read-only signed-in acceptance of the fixed isolated MAIN medical preview.

The dashboard test password is supplied by protected CI secrets, never logged.
Normal session authentication is used; no session forging or reviewer writes.
"""
from __future__ import annotations
import hashlib
import re
from html.parser import HTMLParser
import http.cookiejar
import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, HTTPCookieProcessor, Request, build_opener

SITE = 'https://pdufa-new-dashboard-git-feature-medical-stage4-ver-efe117-pdufa.vercel.app'
BACKEND = 'https://pdufa-medical-intelligence-preview.onrender.com'
PILOT = 'NCT06081894'

class VerificationError(RuntimeError):
    pass

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise VerificationError('UNEXPECTED_REDIRECT')

def request(client, path, *, body=None, origin=None, backend=False):
    base = BACKEND if backend else SITE
    if not path.startswith('/') or path.startswith('//'):
        raise VerificationError('INVALID_FIXED_ORIGIN_PATH')
    headers = {'Accept':'application/json', 'User-Agent':'MAIN-medical-read-acceptance/1'}
    if body is not None:
        headers['Content-Type'] = 'application/json'
    if origin:
        headers['Origin'] = origin
    req = Request(base + path, data=None if body is None else json.dumps(body).encode(), headers=headers)
    try:
        response = client.open(req, timeout=35)
    except HTTPError as exc:
        response = exc
    with response:
        content = response.read(5_000_001)
        if len(content) > 5_000_000:
            raise VerificationError('RESPONSE_TOO_LARGE')
        if 'json' not in response.headers.get('content-type',''):
            raise VerificationError('NON_JSON_RESPONSE')
        return response.code, json.loads(content)

def demand(condition, code):
    if not condition:
        raise VerificationError(code)


class VisibleText(HTMLParser):
    """Collect server-rendered visible text; never print authentication cookies."""
    def __init__(self):
        super().__init__()
        self.parts = []
        self.suppressed = 0
    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'noscript'):
            self.suppressed += 1
    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript'):
            self.suppressed = max(0, self.suppressed - 1)
    def handle_data(self, data):
        if not self.suppressed:
            self.parts.append(data)


def confirm_provisional_score_page(client):
    """Live HTTP/HTML proof of published, NOT automatically updated, scores."""
    path = '/predictions/assessment?nct=' + PILOT
    req = Request(SITE + path, headers={
        'Accept': 'text/html', 'User-Agent': 'MAIN-provisional-score-page-acceptance/1'
    })
    try:
        reply = client.open(req, timeout=40)
    except HTTPError as exc:
        reply = exc
    with reply:
        demand(reply.code == 200, 'SIGNED_IN_PREDICTIONS_PAGE_UNAVAILABLE_HTTP_' + str(reply.code))
        demand('text/html' in reply.headers.get('content-type', ''), 'PREDICTIONS_PAGE_NOT_HTML')
        page = reply.read(5_000_001)
        demand(len(page) <= 5_000_000, 'PREDICTIONS_PAGE_TOO_LARGE')
    parser = VisibleText()
    parser.feed(page.decode('utf-8', 'replace'))
    visible = ' '.join(parser.parts)
    normalized = re.sub(r'\s+', ' ', visible)
    demand('PROVISIONAL RESEARCH ASSESSMENT' in normalized and
           'Initial scientific evidence direction' in normalized and
           'Hypothetical FDA pathway simulator' in normalized and
           'Reset to observed state' in normalized and
           'Actual FDA prediction: ABSTAIN' in normalized and
           'No numeric probabilities or confidence intervals' in normalized,
           'PROVISIONAL_HYPOTHETICAL_PANEL_NOT_RENDERED')
    print(json.dumps({'stage':'PROVISIONAL_FDA_PATHWAY_UI_READ','status':'PASS',
       'nct':PILOT,'researchOnly':True,'publishedPrimaryPositive':2,
       'sourceMappedMethods':18,'authorizedGrades':0,
       'hypotheticalOnly':True,'fdaOutcome':'ABSTAIN','accuracy':'NOT_CALIBRATED'}),flush=True)
    demand('Quantitative scientific evidence' in normalized and
           'Assessment 5.1 · Scientific method 12' in normalized and
           'Assessment 5.3 · Scientific method 19' in normalized,
           'QUANTITATIVE_SCIENTIFIC_METHODS_NOT_RENDERED')
    demand('9.69 pp' in normalized and '5.48 pp' in normalized,
           'QUANTITATIVE_SAFETY_ARITHMETIC_NOT_RENDERED')
    demand('not a 0–5 efficacy grade' in normalized and
           'Final FDA prediction: ABSTAIN' in normalized,
           'QUANTITATIVE_CLINICAL_GRADE_FIREWALL_MISSING')
    print(json.dumps({'stage':'QUANTITATIVE_SCIENCE_PAGE_READ','status':'PASS',
       'nct':PILOT,'efficacyMethod':'5.1/L12','safetyMethod':'5.3/L19',
       'publishedDirectionalPrimaryResults':'2/2',
       'unadjustedSafetyRiskDifferencePp':[9.69,5.48],
       'independentClinicalGrades':0,'fdaPrediction':'ABSTAIN'}),flush=True)
    demand('Original-source gap audit' in normalized and
           'did not list a statistical analysis plan' in normalized and
           'NOT RECONCILED' in normalized,
           'SAP_AND_HF_SOURCE_RECONCILIATION_PANEL_NOT_RENDERED')
    demand(b'actions/runs/42555289486' in page,
           'SOURCE_RECONCILIATION_RECEIPT_LINK_NOT_RENDERED')
    demand('Original evidence acquisition' in normalized and
           'Expand six original evidence requests' in normalized and
           'Download unsent inquiry draft' in normalized and
           'Open versioned acquisition packet' in normalized and
           'No request has been sent' in normalized,
           'ORIGINAL_EVIDENCE_HANDOFF_NOT_RENDERED')
    demand(b'/api/predictions/medical-evidence-acquisition?nct=NCT06081894' in page,
           'ORIGINAL_EVIDENCE_ACQUISITION_ENDPOINT_NOT_LINKED')
    demand('Original document intake' in normalized and
           'Open original-document metadata precheck' in normalized and
           'Check metadata only' in normalized and
           'No file upload' in normalized,
           'CLIENT_LOCAL_SHA256_INTAKE_FORM_NOT_RENDERED')
    demand('Encrypted original-document vault' in normalized and
           'STAGED IN BACKEND CODE' in normalized and
           'NOT ACTIVATED' in normalized and
           'NOT ACTIVE' in normalized and
           'Original documents deposited' in normalized and
           'Disposable PostgreSQL 16 acceptance' in normalized and
           'Separate database migration and runtime roles' in normalized and
           'SELECT and INSERT only' in normalized and
           'offline synthetic key-recovery drill' in normalized and
           'AES-256-GCM' in normalized,
           'STAGED_ENCRYPTED_VAULT_NOT_TRUTHFULLY_VISIBLE')
    demand(b'actions/runs/42562929833' in page,
           'DISPOSABLE_POSTGRES_RECEIPT_NOT_LINKED')
    demand(b'actions/runs/42564391773' in page,
           'DISPOSABLE_POSTGRES_LEAST_PRIVILEGE_RECEIPT_NOT_LINKED')
    demand('Alternative source recovery' in normalized and
           'final locked primary SAP' in normalized and
           'no request has been sent' in normalized and
           'medicalaffairs@cytokinetics.com' in normalized,
           'ALTERNATIVE_RESEARCH_ACCESS_ROUTE_NOT_RENDERED')
    demand(b'actions/runs/42556948533' in page,
           'ALTERNATIVE_PUBLIC_SOURCE_AUDIT_LINK_MISSING')
    demand('Phase III scientific review queue' in normalized and
           'Open all 18 research method leads' in normalized and
           'Export all 18 source leads as CSV' in normalized and
           'Authorized clinical grades' in normalized,
           'PILOT_SOURCE_REVIEW_QUEUE_NOT_RENDERED')
    demand(b'/api/predictions/medical-phase3-review-queue?nct=NCT06081894' in page,
           'SOURCE_REVIEW_QUEUE_LINK_MISSING')
    demand('Evidence-quality rubric' in normalized and
           'Show grading anchors for 0, 1, 2, 3, 4, 5' in normalized and
           'Current numerical grade: not assigned' in normalized,
           'CLINICAL_GRADE_RUBRIC_NOT_RENDERED')
    demand('Open versioned independent-review handoff (JSON)' in normalized,
           'SCIENTIFIC_REVIEW_HANDOFF_LINK_NOT_VISIBLE')
    demand('FIRST PRELIMINARY RESEARCH SCORE' in normalized,
           'FIRST_RESEARCH_CHECKLIST_NOT_RENDERED')
    demand('Additional preliminary research scores' in normalized,
           'ADDITIONAL_RESEARCH_CHECKLISTS_NOT_RENDERED')
    demand('AUTOMATIC DOCUMENTARY SCORE RECHECK' in normalized and
           'Check sources now' in normalized and
           'every 15 minutes' in normalized,
           'AUTO_REFRESH_PANEL_NOT_RENDERED')
    demand('Archived evidence checks and overnight monitoring' in normalized and
           'Nightly schedule: CONFIGURED ON MAIN' in normalized and
           'first clock-triggered' in normalized,
           'INACTIVE_NIGHTLY_SOURCE_ARCHIVE_STATUS_NOT_VISIBLE')
    demand(b'main-acacia-public-evidence-nightly.yml' in page,
           'EVIDENCE_HISTORY_ARCHIVE_LINK_MISSING')
    demand('Assessment 5.1' in normalized and 'Assessment 4.2' in normalized and
           'Assessment 5.3' in normalized, 'PILOT_CHECKLIST_IDENTITIES_NOT_RENDERED')
    # Require values adjacent to the associated assessment, not just a stray
    # number elsewhere in the 800-row page.
    for assessment, expected in [('5.1', '3'), ('4.2', '3'), ('5.3', '2')]:
        pattern = r'Assessment ' + re.escape(assessment) + r'.{0,350}?' + expected + r'\s*/\s*5'
        demand(re.search(pattern, normalized, re.DOTALL) is not None,
               'EXPECTED_PROVISIONAL_SCORE_NOT_RENDERED_' + assessment.replace('.', '_'))
    demand('NOT CALIBRATED' in normalized and 'ABSTAIN' in normalized,
           'UNVALIDATED_FDA_OUTPUT_RELEASED')
    demand('document' in normalized.lower() and 'not' in normalized.lower() and
           'clinical' in normalized.lower(), 'RESEARCH_SCORE_LABEL_MISSING')
    print(json.dumps({'stage':'PROVISIONAL_SCORE_PAGE_READ','status':'PASS',
       'nct':PILOT,'publishedResearchScores':[
          {'assessment':'5.1','documentaryReadiness':'3/5'},
          {'assessment':'4.2','documentaryReadiness':'3/5'},
          {'assessment':'5.3','documentaryReadiness':'2/5'}],
       'documentSnapshotDate':'2026-11-08',
       'automaticSourceReassessment':False,
       'clinicalGradesCertified':False,'fdaPrediction':'ABSTAIN'}), flush=True)

def matrix_snapshot(data):
    review = data.get('review', {})
    demand(review.get('nct') == PILOT and review.get('totalPositions') == 800, 'WRONG_MATRIX_IDENTITY')
    demand(review.get('fdaPredictions') == {'APPROVAL':'ABSTAIN','CRL':'ABSTAIN','REVIEW_DELAY':'ABSTAIN'} and
           review.get('certainty') == 'NOT_VALIDATED', 'UNVALIDATED_FORECAST_RELEASED')
    rows = review.get('assessments', [])
    demand(len(rows) == 40 and [r.get('assessmentIndex') for r in rows] == list(range(1,41)), 'INVALID_ASSESSMENT_COVERAGE')
    counts = review.get('counts', {})
    demand(set(counts) == {'SCORED','NOT_APPLICABLE','RETRACTED','STALE_PHASE','UNREVIEWED','VERIFY_PHASE'} and
           all(type(n) is int and n >= 0 for n in counts.values()) and sum(counts.values()) == 800, 'INVALID_METHOD_COUNTS')
    if not review.get('phaseEventId'):
        demand(counts.get('SCORED') == 0 and all(r.get('scoreOutOf100') is None for r in rows), 'UNREVIEWED_EVIDENCE_SCORED')
    return {'phaseEventId':review.get('phaseEventId'), 'counts':counts,
            'historicalReviewEvents':review.get('historicalReviewEvents'),
            'recordedGapEvents':review.get('recordedGapEvents'), 'assessments':rows}

def main():
    password = os.environ.get('DASHBOARD_PASSWORD')
    if not password:
        raise VerificationError('MISSING_AUTHORIZED_DASHBOARD_TEST_SECRET')
    anon = build_opener(NoRedirect())
    endpoint = '/api/predictions/medical-matrix?nct=' + PILOT
    status, _ = request(anon, endpoint)
    demand(status == 401, 'ANONYMOUS_MATRIX_NOT_REJECTED')
    status, _ = request(anon, '/api/predictions/medical-provisional-refresh?nct=' + PILOT)
    demand(status == 401, 'ANONYMOUS_PROVISIONAL_REFRESH_NOT_REJECTED')
    status, _ = request(anon, '/api/predictions/medical-phase3-reviewer-handoff?nct=' + PILOT)
    demand(status == 401, 'ANONYMOUS_REVIEWER_HANDOFF_NOT_REJECTED')
    status, _ = request(anon, '/api/predictions/medical-phase3-review-queue?nct=' + PILOT)
    demand(status == 401, 'ANONYMOUS_REVIEW_QUEUE_NOT_REJECTED')
    status, _ = request(anon, '/api/predictions/medical-evidence-acquisition?nct=' + PILOT)
    demand(status == 401, 'ANONYMOUS_ACQUISITION_PACKET_NOT_REJECTED')
    status, _ = request(anon, '/api/predictions/medical-evidence-intake-precheck?nct=' + PILOT,
                        body={'nct':PILOT}, origin=SITE)
    demand(status == 401, 'ANONYMOUS_EVIDENCE_INTAKE_PRECHECK_NOT_REJECTED')
    status, _ = request(anon, '/api/internal/medical-assessments/coverage', backend=True)
    demand(status == 401, 'ANONYMOUS_BACKEND_NOT_REJECTED')
    client = build_opener(NoRedirect(), HTTPCookieProcessor(http.cookiejar.CookieJar()))
    status, _ = request(client, '/api/auth', body={'password':password}, origin='https://invalid.example')
    demand(status == 403, 'CROSS_ORIGIN_LOGIN_NOT_REJECTED')
    status, _ = request(client, '/api/auth', body={'password':password}, origin=SITE)
    demand(status == 200, 'AUTHORIZED_TEST_LOGIN_FAILED')
    print(json.dumps({'stage':'NORMAL_DASHBOARD_LOGIN','status':'PASS'}), flush=True)
    confirm_provisional_score_page(client)
    status, evidence = request(client, '/api/predictions/medical-evidence-acquisition?nct=' + PILOT)
    demand(status == 200 and evidence.get('schema') == 'MAIN_ACACIA_EVIDENCE_ACQUISITION_HANDOFF_V1'
           and evidence.get('nct') == PILOT
           and evidence.get('protocol') == 'CY 6033'
           and evidence.get('requestCount') == 6
           and evidence.get('mappedMethodPositionsCovered') == 18
           and evidence.get('unmappedPositionsUnreviewed') == 782
           and evidence.get('requestDeliveryStatus') == 'DRAFT_ONLY_NOT_SENT'
           and evidence.get('approvedClinicalGrades') == 0
           and evidence.get('independentPhaseSignoffs') == 0
           and evidence.get('externallyAuthenticatedNewDocuments') == 0
           and evidence.get('fdaPrediction') == 'ABSTAIN'
           and evidence.get('accuracy') == 'NOT_CALIBRATED',
           'EVIDENCE_ACQUISITION_HANDOFF_SCHEMA_OR_SAFETY_FAILED')
    requests = evidence.get('requests',[])
    all_positions = set(sum((x.get('mappedMethodPositions',[]) for x in requests),[]))
    demand(len(requests) == 6 and len(all_positions) == 18
           and len({x.get('requestId') for x in requests}) == 6
           and all(x.get('acquisitionState') == 'DRAFT_NOT_SENT'
              and x.get('evidenceState') == 'NOT_AUTHENTICATED_FOR_CURRENT_REVIEW'
              and x.get('independentReviewerSigned') is False
              and x.get('officialClinicalGrade') is None for x in requests),
           'SOURCE_REQUEST_NOT_SIX_COMPLETE_UNSCORED_REQUIREMENTS')
    status, _ = request(client, '/api/predictions/medical-evidence-acquisition?nct=NCT00000000')
    demand(status == 422,'WRONG_TRIAL_ACQUISITION_ACCEPTED')
    request_url = SITE + '/api/predictions/medical-evidence-acquisition?nct=' + PILOT + '&format=txt'
    with client.open(Request(request_url, headers={'Accept':'text/plain'}), timeout=30) as response:
        text_blob = response.read(30_001)
        demand(response.code == 200 and len(text_blob) <= 30_000
               and 'text/plain' in response.headers.get('content-type','')
               and b'DRAFT' in text_blob and b'NOT SENT' in text_blob
               and b'1. Final locked' in text_blob
               and b'6. Source-verified FDA' in text_blob
               and b'medicalaffairs@cytokinetics.com' in text_blob,
               'ACQUISITION_UNSENT_TEXT_DRAFT_INVALID')
    print(json.dumps({'stage':'ORIGINAL_EVIDENCE_ACQUISITION_HANDOFF','status':'PASS',
       'trial':PILOT,'requestedOriginalEvidenceGates':6,
       'methodsCovered':18,'sourceDocumentsAuthenticated':0,'emailsSent':0,
       'officialClinicalGrades':0,'fdaPrediction':'ABSTAIN'}),flush=True)
    # Synthetic metadata only; no source file upload or medical ledger write.
    metadata = {
      'nct':PILOT,'requestId':'LOCKED_PRIMARY_SAP',
      'documentType':'STATISTICAL_ANALYSIS_PLAN',
      'documentTitle':'Original ACACIA HCM analysis plan metadata example',
      'documentVersion':'Draft 1.0','documentDate':'2026-11-01',
      'sourceUrl':'https://clinicaltrials.gov/study/NCT06081894',
      'claimedSha256':'a'*64
    }
    intake_url='/api/predictions/medical-evidence-intake-precheck?nct=' + PILOT
    status, precheck = request(client, intake_url, body=metadata, origin=SITE)
    demand(status == 200 and precheck.get('schema') == 'MAIN_ACACIA_EVIDENCE_INTAKE_PRECHECK_V1'
           and precheck.get('requestId') == 'LOCKED_PRIMARY_SAP'
           and precheck.get('inputCheck') == 'METADATA_FORMAT_CHECKED_ONLY'
           and precheck.get('issueCodes') == []
           and len(precheck.get('linkedMethodPositions',[])) == 8
           and precheck.get('sourceContentRetrieved') is False
           and precheck.get('claimedDocumentHashVerifiedFromOriginalBytes') is False
           and precheck.get('documentVersionAuthenticated') is False
           and precheck.get('sponsorDataSharingAuthorizationVerified') is False
           and precheck.get('clinicalReviewerSignedOff') is False
           and precheck.get('acceptedForClinicalScoring') is False
           and precheck.get('gradeEventsWritten') == 0
           and precheck.get('persisted') is False
           and precheck.get('uploadsReceived') == 0
           and precheck.get('emailSent') is False
           and precheck.get('fdaPrediction') == 'ABSTAIN'
           and precheck.get('accuracy') == 'NOT_CALIBRATED',
           'EVIDENCE_INTAKE_PRECHECK_NOT_SAFE_OR_MISSING')
    status, _ = request(client, intake_url, body=metadata, origin='https://invalid.example')
    demand(status == 403,'CROSS_ORIGIN_INTAKE_PRECHECK_ACCEPTED')
    wrong=dict(metadata,sourceUrl='https://127.0.0.1/private')
    status, bad = request(client, intake_url, body=wrong, origin=SITE)
    demand(status == 422 and 'UNSUPPORTED_OR_UNSAFE_SOURCE_URL' in bad.get('issueCodes',[])
           and bad.get('gradeEventsWritten') == 0
           and bad.get('acceptedForClinicalScoring') is False,
           'UNSAFE_EVIDENCE_SOURCE_ACCEPTED')
    wrong=dict(metadata,nct='NCT00000000')
    status, bad = request(client, intake_url, body=wrong, origin=SITE)
    demand(status == 422 and 'WRONG_TRIAL' in bad.get('issueCodes',[]),
           'WRONG_TRIAL_EVIDENCE_INTAKE_ACCEPTED')
    print(json.dumps({'stage':'EVIDENCE_INTAKE_METADATA_PREFLIGHT','status':'PASS',
      'nct':PILOT,'methodLinks':8,'originalDocumentBytesUploaded':0,
      'sourceAuthentications':0,'reviewSignatures':0,
      'clinicalGradeEvents':0,'fdaPrediction':'ABSTAIN'}),flush=True)
    status, review_queue = request(client, '/api/predictions/medical-phase3-review-queue?nct=' + PILOT)
    demand(status == 200 and review_queue.get('schema') == 'MAIN_ACACIA_PHASE3_REVIEW_QUEUE_V1'
           and review_queue.get('nct') == PILOT and
           review_queue.get('fdaPrediction') == 'ABSTAIN' and
           review_queue.get('calibratedAccuracy') is None and
           review_queue.get('status') == 'RESEARCH_WORKLIST_NOT_CLINICAL_GRADE',
           'PILOT_RESEARCH_QUEUE_NOT_READ_ONLY')
    summary = review_queue.get('summary', {})
    positions = review_queue.get('positions', [])
    demand(summary.get('mappedSourceLeads') == 18 and
           summary.get('documentChecklist') == 3 and
           summary.get('quantitativeMethods') == 2 and
           summary.get('sourceLeadOnly') == 13 and
           summary.get('positionsNotSourceMapped') == 782 and
           summary.get('officialClinicalGrades') == 0 and
           summary.get('qualifiedPhaseSignoffs') == 0 and
           len(positions) == 18 and
           len(set(x.get('id') for x in positions)) == 18 and
           [x.get('reviewOrder') for x in positions] == list(range(1, 19)) and
           all(x.get('clinicalGrade') is None and
               x.get('qualifiedReviewerSignoff') is False and
               x.get('fdaProbability') is None for x in positions),
           'SOURCE_REVIEW_QUEUE_COUNTS_OR_SAFETY_INVALID')
    alternative=review_queue.get('alternativeSourceRecovery', {})
    source_states=alternative.get('publicRetrievalStatuses', {})
    demand(alternative.get('archivedAuditRun') == 42556948533 and
           alternative.get('sourceCheckDate') == '2026-11-09' and
           len(source_states) == 3 and
           set(source_states.values()) == {'UNAVAILABLE'} and
           alternative.get('sponsorResearchContact') == 'medicalaffairs@cytokinetics.com' and
           alternative.get('finalLockedPrimarySapAuthenticated') is False and
           alternative.get('primarySensitivityRecalculated') is False and
           alternative.get('hfSafetySourcesReconciled') is False and
           alternative.get('automaticRequestSent') is False,
           'ALTERNATIVE_SOURCE_AUDIT_OR_ACCESS_POLICY_INVALID')
    audited=[x for x in positions if x.get('sourceGapAuditRun') == 42555289486]
    demand(len(audited) == 12 and
           all(isinstance(x.get('sourceGapAuditNote'),str) and
               (('SAP' in x['sourceGapAuditNote']) or
                ('12 versus 3 placebo' in x['sourceGapAuditNote'])) for x in audited) and
           all(x.get('clinicalGrade') is None for x in audited),
           'PUBLIC_SOURCE_GAP_NOT_ATTACHED_TO_METHOD_WORKLIST')
    status, _ = request(client, '/api/predictions/medical-phase3-review-queue?nct=NCT00000000')
    demand(status == 422,'WRONG_TRIAL_REVIEW_QUEUE_ACCEPTED')
    csv_req = Request(SITE + '/api/predictions/medical-phase3-review-queue?nct=' + PILOT + '&format=csv',
                      headers={'Accept':'text/csv'})
    with client.open(csv_req, timeout=30) as csv_response:
        csv_blob = csv_response.read(250_001)
        demand(csv_response.code == 200 and
               'text/csv' in csv_response.headers.get('content-type','') and
               len(csv_blob) <= 250_000 and
               csv_blob.count(b'\r\n') == 19 and
               b'UNSCORED' in csv_blob and b'ABSTAIN' in csv_blob and
               b'Public source gap (dated audit)' in csv_blob and
               b'final locked SAP remains unverified' in csv_blob,
               'SCIENTIFIC_REVIEW_QUEUE_CSV_INVALID')
    print(json.dumps({'stage':'PHASE3_REVIEW_QUEUE_READ','status':'PASS',
      'nct':PILOT,'sourceMappedLeads':18,'researchCheckedPositions':5,
      'sourceOnlyLeads':13,'notSourceMapped':782,
      'auditedSourceGapPositions':len(audited),
      'alternateAuditRun':42556948533,'unavailableAlternativeSourceCount':3,
      'automaticSponsorRequestsSent':0,
      'authorizedClinicalGrades':0,'exportLines':19,'fdaPrediction':'ABSTAIN'}),flush=True)
    status, rubric = request(client, '/api/predictions/medical-phase3-reviewer-handoff?nct=' + PILOT)
    demand(status == 200 and rubric.get('schema') == 'MAIN_PHASE3_REVIEWER_HANDOFF_V1'
           and rubric.get('exactNct') == PILOT and rubric.get('protocolCode') == 'CY 6033'
           and rubric.get('officialMethodGradeEventsWritten') == 0
           and rubric.get('finalFdaPrediction') == 'ABSTAIN'
           and rubric.get('authorizedForClinicalWrite') is False
           and rubric.get('missingDataAreNotZeroGrades') is True,
           'SCIENTIFIC_RUBRIC_HANDOFF_NOT_READ_ONLY')
    methods = rubric.get('clinicalQualityRubric',{}).get('methods',[])
    demand(len(methods) == 2
           and [(m.get('assessmentId'),m.get('methodIndex')) for m in methods] == [('5.1',12),('5.3',19)]
           and all(len(m.get('gradeBands',[])) == 6 and
                   len(m.get('requirements',[])) == 6 and
                   m.get('numericGrade') is None and
                   m.get('reviewerSignature') is None for m in methods),
           'CLINICAL_METHOD_RUBRIC_NOT_COMPLETE_OR_UNVERIFIED_GRADE')
    print(json.dumps({'stage':'SIGNED_CLINICAL_QUALITY_RUBRIC_READ','status':'PASS',
         'nct':PILOT,'rubricMethods':['5.1/L12','5.3/L19'],
         'sixPointGradesAssigned':0,'requiredEvidenceChecks':12,
         'authorization':'READ_ONLY','fdaPrediction':'ABSTAIN'}),flush=True)
    status, refreshed = request(client, '/api/predictions/medical-provisional-refresh?nct=' + PILOT)
    demand(status == 200 and refreshed.get('schema') == 'MAIN_PILOT_DOCUMENTARY_REFRESH_V1' and
           refreshed.get('nct') == PILOT and refreshed.get('fdaPrediction') == 'ABSTAIN' and
           refreshed.get('accuracy') == 'NOT_CALIBRATED' and
           refreshed.get('officialClinicalMethodGrades') == 0 and
           refreshed.get('independentPhaseVerified') is False and
           refreshed.get('automaticClinicalRescore') is False,
           'PROVISIONAL_REFRESH_GATE_FAILED')
    pairs = [(x.get('assessmentId'), x.get('points'), x.get('outOf')) for x in refreshed.get('cards', [])]
    demand(pairs == [('5.1',3,5),('4.2',3,5),('5.3',2,5)],
           'PROVISIONAL_REFRESH_SCORE_DRIFT')
    source_states = {p.get('sourceId'):p.get('status') for p in refreshed.get('probes',[])}
    candidates = refreshed.get('newEvidenceCandidates', [])
    demand(isinstance(candidates,list) and
           all(isinstance(item,str) and len(item) <= 100 for item in candidates),
           'UNSAFE_RESEARCH_CANDIDATE_FEED')
    demand(set(source_states)=={'REGISTRY','NEJM_PIVOTAL'} and
           all(x in ('MATCH','CHANGED','UNAVAILABLE') for x in source_states.values()),
           'PUBLIC_SOURCE_REFRESH_MALFORMED')
    print(json.dumps({'stage':'PROVISIONAL_SOURCE_REFRESH','status':'PASS',
         'researchOnly':True,'sourceStatuses':source_states,
         'currentness':refreshed.get('currentness'),
         'newEvidenceCandidates':candidates,
         'documentaryScores':pairs,'clinicalGrades':0,'fdaPrediction':'ABSTAIN'}),flush=True)
    status, data = request(client, endpoint)
    demand(status == 200, 'AUTHENTICATED_MATRIX_UNAVAILABLE_HTTP_' + str(status))
    before = matrix_snapshot(data)
    positions = set()
    for assessment in range(1,41):
        status, detail = request(client, endpoint + '&assessmentIndex=' + str(assessment))
        demand(status == 200 and matrix_snapshot(detail) == before, 'REVIEW_SNAPSHOT_CHANGED')
        selected = detail['review'].get('selectedAssessment', {})
        methods = selected.get('methods', [])
        demand(selected.get('assessmentIndex') == assessment and len(methods) == 20, 'INVALID_METHOD_DETAILS')
        for method in methods:
            index = method.get('methodIndex')
            demand(type(index) is int and 1 <= index <= 20, 'INVALID_METHOD_IDENTITY')
            demand(isinstance(method.get('history'),list) and isinstance(method.get('sourceEvidence'),list), 'MISSING_HISTORY_OR_EVIDENCE')
            if method.get('status') != 'SCORED':
                demand(method.get('grade') is None, 'UNREVIEWED_METHOD_GRADED')
            positions.add((assessment,index))
    demand(len(positions) == 800, 'INCOMPLETE_800_METHOD_COVERAGE')
    print(json.dumps({'stage':'AUTHENTICATED_MATRIX_READ','status':'PASS','assessments':40,
                      'methodPositions':len(positions),'historyUnchanged':True}), flush=True)
    for invalid in ('&assessmentIndex=41', '&assessmentIndex=0'):
        status, _ = request(client, endpoint + invalid)
        demand(status == 422, 'INVALID_POSITION_NOT_REJECTED')
    status, _ = request(client, '/api/predictions/medical-matrix?nct=NCT00000000')
    demand(status == 422, 'NON_FOCUS_NCT_NOT_REJECTED')
    status, installation = request(client, '/api/predictions/medical-installation')
    demand(status == 200 and installation.get('installation',{}).get('state') == 'OBSERVED', 'INSTALLATION_LEDGER_UNAVAILABLE')
    status, audit = request(client, '/api/predictions/medical-method-audit?nct=' + PILOT)
    demand(status == 200 and audit.get('nct') == PILOT, 'PILOT_SOURCE_AUDIT_UNAVAILABLE')
    demand(audit.get('gradeEventsWritten') == 0 and audit.get('scientificReviewEventsWritten') == 0, 'SOURCE_AUDIT_CREATED_CLINICAL_GRADES')
    status, after = request(client, endpoint)
    demand(status == 200 and matrix_snapshot(after) == before, 'READ_ONLY_VERIFICATION_CHANGED_HISTORY')
    print(json.dumps({'status':'PASS','kind':'AUTHENTICATED_ISOLATED_HTTP_READBACK', 'nct':PILOT,
        'assessments':40,'methodPositions':len(positions),'recordedGrades':before['counts'].get('SCORED'),
        'historicalReviewEvents':before['historicalReviewEvents'],'sourceAuditPositions':audit.get('completedPositions'),
        'snapshotSha256':hashlib.sha256(json.dumps(before,sort_keys=True).encode()).hexdigest(),
        'scientificSignoff':False,'predictions':'ABSTAIN','accuracy':'NOT_CALIBRATED'}))

if __name__ == '__main__':
    try:
        main()
    except VerificationError as exc:
        print(json.dumps({'status':'BLOCKED','code':str(exc)}))
        sys.exit(1)
    except (URLError, TimeoutError, ValueError, KeyError, TypeError):
        print(json.dumps({'status':'BLOCKED','code':'ISOLATED_READ_VERIFICATION_FAILED'}))
        sys.exit(1)

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
    status, _ = request(anon, '/api/internal/medical-assessments/coverage', backend=True)
    demand(status == 401, 'ANONYMOUS_BACKEND_NOT_REJECTED')
    client = build_opener(NoRedirect(), HTTPCookieProcessor(http.cookiejar.CookieJar()))
    status, _ = request(client, '/api/auth', body={'password':password}, origin='https://invalid.example')
    demand(status == 403, 'CROSS_ORIGIN_LOGIN_NOT_REJECTED')
    status, _ = request(client, '/api/auth', body={'password':password}, origin=SITE)
    demand(status == 200, 'AUTHORIZED_TEST_LOGIN_FAILED')
    print(json.dumps({'stage':'NORMAL_DASHBOARD_LOGIN','status':'PASS'}), flush=True)
    confirm_provisional_score_page(client)
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

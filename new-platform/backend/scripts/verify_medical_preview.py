"""Read-only signed-in acceptance of the fixed isolated MAIN medical preview.

The dashboard test password is supplied by protected CI secrets, never logged.
Normal session authentication is used; no session forging or reviewer writes.
"""
from __future__ import annotations
import hashlib
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
    status, _ = request(anon, '/api/internal/medical-assessments/coverage', backend=True)
    demand(status == 401, 'ANONYMOUS_BACKEND_NOT_REJECTED')
    client = build_opener(NoRedirect(), HTTPCookieProcessor(http.cookiejar.CookieJar()))
    status, _ = request(client, '/api/auth', body={'password':password}, origin='https://invalid.example')
    demand(status == 403, 'CROSS_ORIGIN_LOGIN_NOT_REJECTED')
    status, _ = request(client, '/api/auth', body={'password':password}, origin=SITE)
    demand(status == 200, 'AUTHORIZED_TEST_LOGIN_FAILED')
    print(json.dumps({'stage':'NORMAL_DASHBOARD_LOGIN','status':'PASS'}), flush=True)
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

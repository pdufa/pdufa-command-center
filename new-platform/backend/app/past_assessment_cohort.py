"""Append-only, verified PAST FDA-event -> exact trial roster.

The 2026 queue is an unverified research manifest. No ticker/date match,
historical approval label, or Phase-3 completion alone qualifies an event.
Only a separately reviewed exact application/decision/evidence association
can activate a whole-PAST assessment cohort.
"""
from __future__ import annotations

from datetime import date
import json
from pathlib import Path
from sqlalchemy import inspect, text

from . import assessment_runtime as runtime

MANIFEST = Path(__file__).parent / 'data' / 'past_2026_assessment_events.json'


def expected(year):
    if year != 2026:
        return None
    data = json.loads(MANIFEST.read_text())
    if data['schemaVersion'] != 1 or data['year'] != 2026:
        raise ValueError('PAST cohort manifest identity mismatch')
    events = data['events']
    if not events or len({e['eventKey'] for e in events}) != len(events):
        raise ValueError('PAST cohort manifest duplicates or emptiness')
    if any(not e['eventKey'].startswith(e['ticker'] + '|' + e['queueDate'] + '|') for e in events):
        raise ValueError('PAST cohort manifest identity mismatch')
    return events


def initialize(engine):
    runtime.initialize(engine)
    with engine.begin() as c:
        c.execute(text("""CREATE TABLE IF NOT EXISTS past_assessment_event_links (
          revision_id TEXT PRIMARY KEY, event_key TEXT NOT NULL, application_id TEXT NOT NULL,
          decision_id TEXT NOT NULL, ncts_json TEXT NOT NULL, cutoff_date TEXT NOT NULL,
          evidence_id TEXT NOT NULL, imported_at TEXT NOT NULL, record_hash TEXT NOT NULL)"""))
        c.execute(text("CREATE INDEX IF NOT EXISTS past_assessment_link_event ON past_assessment_event_links(event_key,imported_at)"))
        if engine.dialect.name == 'postgresql':
            trigger = c.execute(text("SELECT 1 FROM pg_trigger WHERE tgname='past_assessment_event_links_immutable'")).scalar()
            if not trigger:
                c.execute(text('CREATE TRIGGER past_assessment_event_links_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON past_assessment_event_links FOR EACH STATEMENT EXECUTE FUNCTION assessment_v2_immutable()'))
        else:
            for action in ('UPDATE', 'DELETE'):
                c.execute(text("CREATE TRIGGER IF NOT EXISTS past_assessment_event_links_" + action.lower() +
                    " BEFORE " + action + " ON past_assessment_event_links BEGIN SELECT RAISE(ABORT,'PAST links are append-only'); END"))


def check_link(engine, record):
    """Verify an independently reviewed exact FDA event identity; never infer by date/ticker."""
    keys = {'eventKey','applicationId','decisionId','ncts','cutoffDate','evidenceId'}
    if set(record) != keys:
        raise ValueError('Exact source-backed PAST link fields required')
    events = expected(int(record['eventKey'].split('|')[1][:4]))
    event = next((e for e in (events or []) if e['eventKey'] == record['eventKey']), None)
    if not event:
        raise ValueError('Unknown PAST event key in frozen source manifest')
    ncts = record['ncts']
    if not isinstance(ncts, list) or not ncts or len(ncts) != len(set(ncts)) or any(
        not isinstance(n, str) or not runtime.NCT.fullmatch(n) for n in ncts
    ):
        raise ValueError('Unambiguous exact NCT trial IDs required')
    try:
        cutoff = date.fromisoformat(record['cutoffDate'])
    except (TypeError, ValueError):
        raise ValueError('A valid pre-decision evidence cutoff is required') from None
    if cutoff.isoformat() != record['cutoffDate']:
        raise ValueError('Invalid cutoff format')
    if not all(inspect(engine).has_table(t) for t in ('phase3_fda_applications','phase3_fda_decisions',
             'phase3_trial_applications','phase3_evidence')):
        raise ValueError('Verified FDA application evidence has not been imported')
    with engine.connect() as c:
        review = c.execute(text("""SELECT d.application_id,d.decision_date,d.pdufa_date,a.application_number,
           a.drug,a.indication FROM phase3_fda_decisions d
           JOIN phase3_fda_applications a ON a.application_id=d.application_id
           WHERE d.decision_id=:id AND d.application_id=:app AND d.verification_status='VERIFIED'"""),
           {'id':record['decisionId'],'app':record['applicationId']}).mappings().first()
        if not review:
            raise ValueError('Exact verified FDA review cycle and application ID required')
        if event['queueDate'] not in (review['pdufa_date'],review['decision_date']):
            raise ValueError('Unverified PAST event date: reconcile the source manifest before linking')
        if not review['decision_date'] or cutoff >= date.fromisoformat(review['decision_date']):
            raise ValueError('Evidence cutoff must precede the verified decision date')
        for nct in ncts:
            linked = c.execute(text("""SELECT 1 FROM phase3_trial_applications l
                JOIN phase3_evidence e ON e.evidence_id=l.evidence_id
                WHERE l.nct_id=:nct AND l.application_id=:app
                AND l.verification_status='VERIFIED' AND e.verification_status='VERIFIED'"""),
                {'nct':nct,'app':record['applicationId']}).scalar()
            if not linked:
                raise ValueError('NCT is not source-verified for this exact application')
        proof = c.execute(text("""SELECT url,document,verification_status,publisher_kind
            FROM phase3_evidence WHERE evidence_id=:id"""), {'id':record['evidenceId']}).mappings().first()
        if not proof or proof['verification_status'] != 'VERIFIED' or proof['publisher_kind'] not in ('FDA','SEC','OFFICIAL_SPONSOR'):
            raise ValueError('A verified primary regulatory identity document is required')
        body = proof['document'].casefold()
        # The scoped application, product and every trial ID must appear in
        # the source; ticker/date coincidence alone is never a proof.
        tokens = [review['application_number'],review['drug'],*ncts]
        if any(token.casefold() not in body for token in tokens):
            raise ValueError('Source text does not establish the event/application/trial identities')
    return {**record,'ncts':sorted(ncts)}


def import_verified_link(engine, record):
    """Operator-controlled intake only, not a browser-write endpoint."""
    checked = check_link(engine, record)
    initialize(engine)
    record_hash = runtime.sha(checked)
    with engine.begin() as c:
        c.execute(text("""INSERT INTO past_assessment_event_links
          (revision_id,event_key,application_id,decision_id,ncts_json,cutoff_date,evidence_id,imported_at,record_hash)
          VALUES(:revision,:event,:app,:decision,:ncts,:cutoff,:proof,:now,:hash)
          ON CONFLICT(revision_id) DO NOTHING"""),
          {'revision':record_hash,'event':checked['eventKey'],'app':checked['applicationId'],
           'decision':checked['decisionId'],'ncts':runtime.packed(checked['ncts']),
           'cutoff':checked['cutoffDate'],'proof':checked['evidenceId'],'now':runtime.now(),'hash':record_hash})
    return record_hash


def roster(engine, year):
    """Read-only whole-year preflight; no outcome labels or future-source substitution."""
    events = expected(year)
    if events is None:
        return {'status':'PAST_YEAR_NOT_IMPORTED','year':year,'total':None,
                'linked':0,'ready':False,'events':[],'tasks':[],
                'source':'NO_VERIFIED_YEAR_ROSTER'}
    latest = {}
    if inspect(engine).has_table('past_assessment_event_links'):
        with engine.connect() as c:
            rows = c.execute(text("""SELECT * FROM past_assessment_event_links
                ORDER BY imported_at DESC,revision_id DESC""")).mappings().all()
        for row in rows:
            if row['event_key'] not in latest:
                latest[row['event_key']] = dict(row)
    output = []
    tasks = []
    for event in events:
        item = {'eventKey':event['eventKey'],'ticker':event['ticker'],
                'queueDate':event['queueDate'],'status':'MISSING_VERIFIED_LINK','ncts':[]}
        saved = latest.get(event['eventKey'])
        if saved:
            try:
                link = {'eventKey':saved['event_key'],'applicationId':saved['application_id'],
                        'decisionId':saved['decision_id'],'ncts':json.loads(saved['ncts_json']),
                        'cutoffDate':saved['cutoff_date'],'evidenceId':saved['evidence_id']}
                if runtime.sha(link) != saved['record_hash']:
                    raise ValueError('Immutable link digest mismatch')
                check_link(engine, link)
                for nct in link['ncts']:
                    request = runtime.RunInput(nct=nct,level=1,mode='BLIND_HISTORICAL',
                                               contract='SCIENTIFIC_1_3',cutoffDate=date.fromisoformat(link['cutoffDate']))
                    runtime.scientific_historical_target(engine, request)
                    runtime.source_for(engine, request)
                item.update(status='READY',ncts=link['ncts'],cutoffDate=link['cutoffDate'],
                            applicationId=link['applicationId'],sourceEvidenceId=link['evidenceId'])
                tasks.extend({'nct':nct,'cutoffDate':link['cutoffDate'],'eventKey':event['eventKey']}
                             for nct in link['ncts'])
            except (ValueError, TypeError, KeyError) as exc:
                item['status'] = 'LINK_OR_PRE_CUTOFF_EVIDENCE_INCOMPLETE'
                item['reason'] = str(exc)[:200]
        output.append(item)
    linked = sum(item['status']=='READY' for item in output)
    # One NCT used across different FDA events requires its own distinct
    # application-cycle request contract before whole-year activation.
    if len({task['nct'] for task in tasks}) != len(tasks):
        for item in output:
            if any(sum(t['nct']==n for t in tasks)>1 for n in item['ncts']):
                item['status']='MULTI_CYCLE_NCT_REQUIRES_EVENT_SCOPED_RUNTIME'
        linked=sum(item['status']=='READY' for item in output)
    # Partial-year operation is an auditable assessment attempt, not a
    # claim that every event has been linked. Never return a task for an event
    # that failed verification, source pre-cutoff checks or cycle disambiguation.
    eligible_keys = {item['eventKey'] for item in output if item['status']=='READY'}
    eligible_tasks = [task for task in tasks if task['eventKey'] in eligible_keys]
    ready = bool(output) and linked == len(output)
    return {'status':'VERIFIED_WHOLE_PAST_COHORT' if ready else 'PAST_RECONCILIATION_INCOMPLETE',
            'year':year,'total':len(output),'linked':linked,'ready':ready,
            'events':output,'tasks':eligible_tasks if ready else [],
            'eligibleTasks':eligible_tasks,
            'source':'APPEND_ONLY_EXACT_EVENT_APPLICATION_TRIAL_ROSTER'}

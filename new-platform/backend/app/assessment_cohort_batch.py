"""Owner-requested single/whole-cohort Levels 1–3, with durable checkpoints.

The manifest is server-derived and immutable. PAST means the actual PAST event
queue, never all old completed registry trials. Unlinked events remain visible
blocked items; neither a ticker match nor an entered NCT establishes FDA identity.
"""
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, StrictInt
from sqlalchemy import inspect, text

from . import assessment_runtime as runtime
from .scientific_trial_assessment import VERSION

DATA = Path(__file__).parent / 'data'
MAX_TRIALS = 500
LEASE = timedelta(minutes=15)


class BatchInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    requestKey: UUID
    population: Literal['FOCUS', 'POOL', 'HISTORICAL']
    scope: Literal['selected', 'all']
    ncts: list[str] = Field(default_factory=list, max_length=MAX_TRIALS)
    levels: list[StrictInt] = Field(default_factory=lambda: [1, 2, 3], min_length=1, max_length=3)
    mode: Literal['CURRENT_EVIDENCE', 'BLIND_HISTORICAL']
    cutoffDate: date | None = None
    inventoryHash: str | None = Field(default=None, pattern=r'^[a-f0-9]{64}$')

    def checked(self):
        if any(l not in (1, 2, 3) for l in self.levels) or len(set(self.levels)) != len(self.levels):
            raise ValueError('Select distinct assessment Levels 1–3')
        if self.scope == 'selected' and (not self.ncts or any(not runtime.NCT.fullmatch(n) for n in self.ncts)):
            raise ValueError('Selected trials require exact NCT IDs')
        if len(set(self.ncts)) != len(self.ncts) or (self.scope == 'all' and self.ncts):
            raise ValueError('Whole lists are resolved by the server; duplicate or caller-supplied memberships are not accepted')
        if self.mode == 'CURRENT_EVIDENCE' and self.cutoffDate is not None:
            raise ValueError('Current evidence cannot accept a historical cutoff')
        if self.mode == 'BLIND_HISTORICAL':
            if self.cutoffDate and self.cutoffDate >= datetime.now(timezone.utc).date():
                raise ValueError('Historical cutoff must be in the past')
            if not self.cutoffDate and not (self.population == 'HISTORICAL' and self.scope == 'all'):
                raise ValueError('A historical evidence cutoff is required')
        if self.population == 'HISTORICAL' and self.mode != 'BLIND_HISTORICAL':
            raise ValueError('PAST batches require cutoff-isolated historical evidence')
        if self.scope == 'all' and not self.inventoryHash:
            raise ValueError('Load the complete source inventory before submitting the whole list')
        return self


def initialize(engine):
    runtime.initialize(engine)
    with engine.begin() as c:
        if engine.dialect.name == 'postgresql':
            c.execute(text('SELECT pg_advisory_xact_lock(839201632)'))
        c.execute(text('''CREATE TABLE IF NOT EXISTS assessment_cohort_batches (
            batch_id TEXT PRIMARY KEY, request_key TEXT NOT NULL UNIQUE,
            request_json TEXT NOT NULL, manifest_json TEXT NOT NULL,
            manifest_hash TEXT NOT NULL, engine_version TEXT NOT NULL, created_at TEXT NOT NULL)'''))
        c.execute(text('''CREATE TABLE IF NOT EXISTS assessment_cohort_workers (
            batch_id TEXT PRIMARY KEY, lease_id TEXT, lease_until TEXT)'''))
        c.execute(text('''CREATE TABLE IF NOT EXISTS assessment_cohort_items (
            batch_id TEXT NOT NULL, item_key TEXT NOT NULL, nct_id TEXT, level INTEGER NOT NULL,
            cutoff_date TEXT, state TEXT NOT NULL, attempts INTEGER NOT NULL,
            run_id TEXT, error TEXT, updated_at TEXT NOT NULL,
            PRIMARY KEY(batch_id,item_key,level))'''))
        c.execute(text('''CREATE TABLE IF NOT EXISTS assessment_past_event_links (
            event_key TEXT PRIMARY KEY, nct_id TEXT NOT NULL, application_id TEXT NOT NULL,
            source_url TEXT NOT NULL, source_hash TEXT NOT NULL, linked_at TEXT NOT NULL)'''))
        for table in ('assessment_cohort_batches', 'assessment_past_event_links'):
            if engine.dialect.name == 'postgresql':
                exists = c.execute(text('SELECT 1 FROM pg_trigger WHERE tgname=:n AND tgrelid=CAST(:t AS regclass)'),
                                   {'n': table+'_immutable', 't': table}).scalar()
                if not exists:
                    c.execute(text(f'CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON {table} FOR EACH STATEMENT EXECUTE FUNCTION assessment_v2_immutable()'))
            else:
                for op in ('UPDATE', 'DELETE'):
                    c.execute(text(f"CREATE TRIGGER IF NOT EXISTS {table}_{op.lower()} BEFORE {op} ON {table} BEGIN SELECT RAISE(ABORT, 'Assessment cohort manifest and identity links are append-only'); END"))


def inventory(engine, population):
    if population == 'HISTORICAL':
        document = json.loads((DATA / 'assessment_past_inventory.json').read_text())
        records = []
        links = {}
        if inspect(engine).has_table('assessment_past_event_links'):
            with engine.connect() as c:
                links = {r['event_key']: dict(r) for r in c.execute(text('SELECT * FROM assessment_past_event_links')).mappings()}
        for event in document['events']:
            row = {**event, 'key': event['eventKey'], 'nct': None, 'cutoffDate': None,
                   'blocker': 'UNLINKED_PAST_EVENT: exact NCT and FDA application link have not been established'}
            link = links.get(event['eventKey'])
            if link:
                try:
                    if not inspect(engine).has_table('phase3_evidence') or not inspect(engine).has_table('phase3_trial_applications'):
                        raise ValueError('MISSING_SOURCED_PAST_LINK: retained original application/trial evidence is required')
                    with engine.connect() as c:
                        receipt = c.execute(text('''SELECT e.evidence_id FROM phase3_trial_applications a
                            JOIN phase3_evidence e ON e.evidence_id=a.evidence_id
                            WHERE a.nct_id=:nct AND a.application_id=:app AND a.verification_status='VERIFIED'
                            AND e.verification_status='VERIFIED' AND e.url=:url AND e.sha256=:hash'''),
                            {'nct': link['nct_id'], 'app': link['application_id'],
                             'url': link['source_url'], 'hash': link['source_hash']}).first()
                    if not receipt:
                        raise ValueError('UNVERIFIED_PAST_LINK_RECEIPT: no matching original trial/application evidence')
                    # This selects verified application identity/date, never the outcome.
                    target = runtime.scientific_historical_target(engine, runtime.RunInput(
                        nct=link['nct_id'], level=1, mode='BLIND_HISTORICAL',
                        cutoffDate=date(1900, 1, 1), contract='SCIENTIFIC_1_3'))
                    if target['application_id'] != link['application_id']:
                        raise ValueError('Historical application identity mismatch')
                    if target['decision_date'][:4] != event['queueDate'][:4]:
                        raise ValueError('PAST event year differs from the sourced application decision; verify the exact review cycle')
                    row.update(nct=link['nct_id'], applicationId=link['application_id'],
                               cutoffDate=(date.fromisoformat(target['decision_date'])-timedelta(days=30)).isoformat(),
                               blocker=None)
                except ValueError as exc:
                    row['blocker'] = str(exc)
            records.append(row)
        source = {'status': 'DATED_PAST_EVENT_QUEUE_NOT_A_COMPLETE_FDA_CENSUS',
                  'asOf': document['asOf'], 'source': document['source']}
    elif population == 'FOCUS':
        from .focus_assessment_batch import roster
        saved = roster(engine)
        if saved:
            members = saved['members']
            source = {'status': saved['authority_status'], 'source': saved['source_url'],
                      'asOf': saved['retrieved_at'], 'rosterId': saved['roster_id']}
        else:
            doc = json.loads((DATA / 'assessment_trial_inventory.json').read_text())
            members = doc['records']
            source = {'status': 'DATED_PACKAGED_OWNER_INVENTORY_NOT_LIVE_SHEET_RECONCILIATION',
                      'source': doc['source'], 'asOf': doc['asOf']}
        records = [{**m, 'key': m['nct'], 'blocker': None, 'cutoffDate': None} for m in members]
    elif population == 'POOL':
        from .source_workspace import workspace
        records = []
        for item in workspace()['pipeline']:
            candidates = [str(item.get(k) or '') for k in ('nct', 'nct_id', 'nctId', 'id')]
            nct = next((v for v in candidates if runtime.NCT.fullmatch(v)), None)
            if nct:
                records.append({'key': nct, 'nct': nct, 'ticker': item.get('ticker', ''),
                                'company': item.get('company', ''), 'cutoffDate': None, 'blocker': None})
        records = list({r['key']: r for r in records}.values())
        source = {'status': 'SOURCE_WORKSPACE_INVENTORY', 'source': 'Existing POOL source workspace'}
    else:
        raise ValueError('Unknown trial population')
    if len(records) > MAX_TRIALS or len({r['key'] for r in records}) != len(records):
        raise ValueError('Oversized or duplicate source inventory; no partial whole-list execution is permitted')
    for row in records:
        if row['nct'] is not None and not runtime.NCT.fullmatch(row['nct']):
            raise ValueError('Invalid exact trial identity in source inventory')
    records.sort(key=lambda r: r['key'])
    return {'population': population, 'source': source, 'records': records,
            'total': len(records), 'blocked': sum(bool(r['blocker']) for r in records),
            'inventoryHash': runtime.sha({'source': source, 'records': records})}


def inventory_page(engine, population, offset=0, limit=50):
    if not 0 <= offset <= MAX_TRIALS or not 1 <= limit <= 100:
        raise ValueError('Invalid inventory page')
    data = inventory(engine, population)
    records = data['records'][offset:offset+limit]
    return {**data, 'records': records, 'nextOffset': offset+len(records) if offset+len(records)<data['total'] else None}


def create(engine, request):
    request.checked()
    initialize(engine)
    request_json = runtime.packed(request.model_dump(mode='json'))
    with engine.connect() as c:
        existing = c.execute(text('SELECT batch_id,request_json FROM assessment_cohort_batches WHERE request_key=:k'),
                             {'k': str(request.requestKey)}).first()
    if existing:
        if existing[1] != request_json:
            raise ValueError('Request key already belongs to a different assessment selection')
        return existing[0]
    if request.scope == 'all':
        inv = inventory(engine, request.population)
        if inv['inventoryHash'] != request.inventoryHash:
            raise ValueError('Source inventory changed; reload it before submitting the entire list')
        records = inv['records']
        source = inv['source']
    else:
        records = [{'key': n, 'nct': n, 'blocker': None, 'cutoffDate': None} for n in sorted(request.ncts)]
        source = {'status': 'OWNER_SELECTED_EXACT_NCTS_NOT_COHORT_MEMBERSHIP_VERIFICATION'}
    if not records:
        raise ValueError('The selected source inventory is empty; no batch was created')
    items = []
    for row in records:
        cutoff = request.cutoffDate.isoformat() if request.cutoffDate else row.get('cutoffDate')
        for level in sorted(request.levels):
            items.append({'key': row['key'], 'nct': row['nct'], 'level': level,
                          'cutoffDate': cutoff, 'blocker': row.get('blocker'),
                          'ticker': row.get('ticker', ''), 'applicationId': row.get('applicationId')})
    manifest = {'population': request.population, 'scope': request.scope, 'mode': request.mode,
                'source': source, 'records': records, 'items': items, 'engineVersion': VERSION}
    batch_id = str(uuid4())
    with engine.begin() as c:
        c.execute(text('''INSERT INTO assessment_cohort_batches VALUES(:id,:key,:request,:manifest,:hash,:version,:at)
            ON CONFLICT(request_key) DO NOTHING'''), {'id': batch_id, 'key': str(request.requestKey),
            'request': request_json, 'manifest': runtime.packed(manifest), 'hash': runtime.sha(manifest),
            'version': VERSION, 'at': runtime.now()})
        saved = c.execute(text('SELECT batch_id,request_json FROM assessment_cohort_batches WHERE request_key=:k'),
                          {'k': str(request.requestKey)}).first()
        if saved[1] != request_json:
            raise ValueError('Conflicting replay of assessment request key')
        batch_id = saved[0]
        c.execute(text('INSERT INTO assessment_cohort_workers VALUES(:b,NULL,NULL) ON CONFLICT(batch_id) DO NOTHING'), {'b': batch_id})
        for item in items:
            c.execute(text('''INSERT INTO assessment_cohort_items VALUES(:batch,:key,:nct,:level,:cutoff,:state,0,NULL,:error,:at)
                ON CONFLICT(batch_id,item_key,level) DO NOTHING'''),
                {'batch': batch_id, 'key': item['key'], 'nct': item['nct'], 'level': item['level'],
                 'cutoff': item['cutoffDate'], 'state': 'BLOCKED' if item['blocker'] else 'PENDING',
                 'error': item['blocker'], 'at': runtime.now()})
    return batch_id


def saved(engine, batch_id):
    try:
        if str(UUID(batch_id)) != batch_id:
            raise ValueError()
    except ValueError:
        raise HTTPException(422, 'Valid batch UUID required') from None
    if not inspect(engine).has_table('assessment_cohort_batches'):
        raise HTTPException(404, 'Saved assessment batch not found')
    with engine.connect() as c:
        row = c.execute(text('SELECT * FROM assessment_cohort_batches WHERE batch_id=:b'), {'b': batch_id}).mappings().first()
        if not row:
            raise HTTPException(404, 'Saved assessment batch not found')
        slots = [dict(r) for r in c.execute(text('SELECT * FROM assessment_cohort_items WHERE batch_id=:b ORDER BY item_key,level'), {'b': batch_id}).mappings()]
    manifest = json.loads(row['manifest_json'])
    if runtime.sha(manifest) != row['manifest_hash']:
        raise HTTPException(503, 'Saved batch manifest integrity failure')
    expected = {(i['key'], i['level']): i for i in manifest['items']}
    if len(slots) != len(expected):
        raise HTTPException(503, 'Saved batch has missing or extra trial/level checkpoints')
    for slot in slots:
        item = expected.get((slot['item_key'], slot['level']))
        if not item or item['nct'] != slot['nct_id'] or item['cutoffDate'] != slot['cutoff_date']:
            raise HTTPException(503, 'Saved batch trial/level identity mismatch')
    return dict(row), manifest, slots


def verified_result(engine, manifest, slot):
    if not slot['run_id']:
        return None
    state = runtime.status(engine, slot['nct_id'], slot['run_id'])
    report = state['report']
    return validate_result(manifest, slot, report)


def validate_result(manifest, slot, report):
    if report and (report['runId'] != slot['run_id'] or report['nct'] != slot['nct_id']
                   or report['level'] != slot['level'] or report['mode'] != manifest['mode']
                   or report['cutoffDate'] != slot['cutoff_date']
                   or report.get('contract') != 'SCIENTIFIC_1_3'
                   or report['engineVersion'] != manifest['engineVersion']+'/level-'+str(slot['level'])):
        raise HTTPException(503, 'Saved batch result identity, cutoff or engine contract mismatch')
    return report


def summary(engine, batch_id):
    row, manifest, slots = saved(engine, batch_id)
    # Read all report receipts in one database round trip; polling a large
    # cohort must not open one remote connection per level item.
    with engine.connect() as c:
        results = {r['run_id']: (r['report_json'], r['report_hash']) for r in c.execute(text('''
            SELECT r.run_id,r.report_json,r.report_hash FROM assessment_v2_results r
            JOIN assessment_cohort_items i ON i.run_id=r.run_id WHERE i.batch_id=:b'''),
            {'b': batch_id}).mappings()}
    items = []
    counts = {key: 0 for key in ('completed', 'blocked', 'failed', 'running', 'pending', 'scored')}
    for slot in slots:
        receipt = results.get(slot['run_id'])
        report = validate_result(manifest, slot, runtime.verified_report(receipt) if receipt else None)
        state = 'COMPLETED' if report else slot['state']
        if state == 'COMPLETED' and not report:
            state = 'FAILED'
        counts[state.lower()] += 1
        counts['scored'] += int(bool(report and report['score']['value'] is not None and report['score']['kind'] != 'LEVEL_SPECIFIC_EVIDENCE_COVERAGE'))
        items.append({'key': slot['item_key'], 'nct': slot['nct_id'], 'level': slot['level'],
                      'cutoffDate': slot['cutoff_date'], 'state': state, 'attempts': slot['attempts'],
                      'runId': slot['run_id'], 'reportHash': report['reportHash'] if report else None,
                      'error': slot['error'] if not report else None,
                      'scientificStatus': report['scientificStatus'] if report else None})
    with engine.connect() as c:
        worker = c.execute(text('SELECT * FROM assessment_cohort_workers WHERE batch_id=:b'), {'b': batch_id}).mappings().first()
    active = bool(worker and worker['lease_until'] and worker['lease_until'] > runtime.now())
    can_resume = any(s['state'] in ('PENDING', 'RUNNING', 'FAILED') and s['attempts'] < 2 for s in slots) and not active
    terminal = not active and not can_resume
    status = ('COMPLETED_WITH_BLOCKERS' if counts['blocked'] or counts['failed'] else 'COMPLETED') if terminal else ('RUNNING' if active else 'RESUMABLE')
    return {'batchId': batch_id, 'population': manifest['population'], 'scope': manifest['scope'],
            'mode': manifest['mode'], 'createdAt': row['created_at'], 'source': manifest['source'],
            'manifestHash': row['manifest_hash'], 'totalTrials': len(manifest['records']),
            'totalItems': len(items), 'counts': counts, 'items': items, 'status': status,
            'canResume': can_resume, 'terminal': terminal,
            'meaning': 'Completed means an immutable research report was retrieved; it does not mean a validated scientific score or FDA prediction.'}


def recent(engine, population):
    if population not in ('POOL', 'FOCUS', 'HISTORICAL'):
        raise ValueError('Unknown trial population')
    if not inspect(engine).has_table('assessment_cohort_batches'):
        return {'batches': []}
    with engine.connect() as c:
        rows = c.execute(text('SELECT batch_id,created_at,manifest_json FROM assessment_cohort_batches ORDER BY created_at DESC,batch_id DESC LIMIT 100')).mappings().all()
    return {'batches': [{'batchId': r['batch_id'], 'createdAt': r['created_at']}
                        for r in rows if json.loads(r['manifest_json'])['population'] == population][:20]}


def execute(engine, batch_id, collector=runtime.collect_registry):
    """Continue the explicitly requested finite manifest, independent of a browser.

    One lease prevents simultaneous resumes. Every level checkpoints separately;
    no completed report is replaced, and failed execution gets at most one retry.
    An expired worker resumes the original run ID, including the save/checkpoint gap.
    """
    _, manifest, _ = saved(engine, batch_id)
    if manifest['engineVersion'] != VERSION:
        raise ValueError('Resume with the original assessment engine version')
    token = str(uuid4())
    with engine.begin() as c:
        claimed = c.execute(text('''UPDATE assessment_cohort_workers SET lease_id=:token,lease_until=:until
            WHERE batch_id=:b AND (lease_until IS NULL OR lease_until<:now)'''),
            {'token': token, 'until': (datetime.now(timezone.utc)+LEASE).isoformat(), 'now': runtime.now(), 'b': batch_id}).rowcount
    if not claimed:
        return
    try:
        _, manifest, slots = saved(engine, batch_id)
        for slot in slots:
            if slot['state'] in ('BLOCKED', 'COMPLETED'):
                continue
            report = verified_result(engine, manifest, slot)
            if report:
                state, error = 'COMPLETED', None
            elif slot['attempts'] >= 2:
                continue
            else:
                with engine.begin() as c:
                    renewed = c.execute(text('UPDATE assessment_cohort_workers SET lease_until=:until WHERE batch_id=:b AND lease_id=:token'),
                        {'until': (datetime.now(timezone.utc)+LEASE).isoformat(), 'b': batch_id, 'token': token}).rowcount
                    if not renewed:
                        return
                    c.execute(text("UPDATE assessment_cohort_items SET state='RUNNING',attempts=attempts+1,updated_at=:at WHERE batch_id=:b AND item_key=:key AND level=:l"),
                              {'b': batch_id, 'key': slot['item_key'], 'l': slot['level'], 'at': runtime.now()})
                try:
                    request = runtime.RunInput(nct=slot['nct_id'], level=slot['level'], mode=manifest['mode'],
                        cutoffDate=slot['cutoff_date'], contract='SCIENTIFIC_1_3').checked()
                    if manifest['mode'] == 'BLIND_HISTORICAL':
                        runtime.source_for(engine, request)  # Refuse before fetching or creating an unsupported run.
                    run_id = slot['run_id'] or runtime.create(engine, request)
                    with engine.begin() as c:
                        c.execute(text('UPDATE assessment_cohort_items SET run_id=:run WHERE batch_id=:b AND item_key=:key AND level=:l'),
                                  {'run': run_id, 'b': batch_id, 'key': slot['item_key'], 'l': slot['level']})
                    slot['run_id'] = run_id
                    runtime.execute(engine, run_id, collector)
                    report = verified_result(engine, manifest, slot)
                    state = 'COMPLETED' if report else 'FAILED'
                    error = None if report else runtime.status(engine, slot['nct_id'], run_id)['error']
                except (ValueError, HTTPException) as exc:
                    state, error = 'BLOCKED', str(exc) if isinstance(exc, ValueError) else str(exc.detail)
                except Exception:
                    state, error = 'FAILED', 'Assessment execution failed; saved checkpoints retained'
            with engine.begin() as c:
                c.execute(text('UPDATE assessment_cohort_items SET state=:state,error=:error,updated_at=:at WHERE batch_id=:b AND item_key=:key AND level=:l'),
                          {'state': state, 'error': error, 'at': runtime.now(), 'b': batch_id, 'key': slot['item_key'], 'l': slot['level']})
    finally:
        with engine.begin() as c:
            c.execute(text('UPDATE assessment_cohort_workers SET lease_id=NULL,lease_until=NULL WHERE batch_id=:b AND lease_id=:token'),
                      {'b': batch_id, 'token': token})


def router(engine_provider, writes):
    api = APIRouter()

    @api.get('/cohort-inventory')
    def get_inventory(population: str = 'FOCUS', offset: int = Query(default=0, ge=0, le=MAX_TRIALS),
                      limit: int = Query(default=50, ge=1, le=100)):
        try:
            return inventory_page(engine_provider(), population, offset, limit)
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from None

    @api.get('/batches')
    def get_batches(population: str = 'FOCUS'):
        try:
            return recent(engine_provider(), population)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None

    @api.get('/batches/{batch_id}')
    def get_batch(batch_id: str):
        return summary(engine_provider(), batch_id)

    @api.post('/batches', status_code=202, dependencies=[Depends(writes)])
    def start_batch(request: BatchInput, tasks: BackgroundTasks):
        db = engine_provider()
        try:
            batch_id = create(db, request)
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from None
        result = summary(db, batch_id)
        if result['canResume']:
            tasks.add_task(execute, db, batch_id)
        return result

    @api.post('/batches/{batch_id}/resume', status_code=202, dependencies=[Depends(writes)])
    def resume_batch(batch_id: str, tasks: BackgroundTasks):
        db = engine_provider()
        result = summary(db, batch_id)
        if result['canResume']:
            tasks.add_task(execute, db, batch_id)
        return result

    return api

"""Isolated, bounded FOCUS L4–L6 original-evidence coverage batches.

These are not calibrated FDA predictions or scientific efficacy scores.
L1–L3 batches, rosters and historical results are never modified.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from sqlalchemy import text, inspect
from . import assessment_runtime as runtime
from . import focus_assessment_batch as focus

VERSION = runtime.VERSION + '/focus-l456'

def create(engine):
    focus.initialize(engine)
    saved = focus.roster(engine)
    if not saved:
        raise ValueError('NO_RECONCILED_FOCUS_DATABASE_ROSTER')
    with engine.begin() as c:
        c.execute(text("""INSERT INTO focus_assessment_batches VALUES(:id,:roster,:version,:at)
            ON CONFLICT(roster_id,engine_version) DO NOTHING"""),
            {'id':str(uuid4()),'roster':saved['roster_id'],'version':VERSION,'at':runtime.now()})
        batch=c.execute(text("""SELECT batch_id FROM focus_assessment_batches
            WHERE roster_id=:r AND engine_version=:v"""),
            {'r':saved['roster_id'],'v':VERSION}).scalar_one()
        for member in saved['members']:
            for level in (4,5,6):
                c.execute(text("""INSERT INTO focus_assessment_items VALUES(
                    :batch,:nct,:level,'PENDING',0,NULL,NULL,:at)
                    ON CONFLICT(batch_id,nct_id,level) DO NOTHING"""),
                    {'batch':batch,'nct':member['nct'],'level':level,'at':runtime.now()})
    return batch

def execute(engine,batch_id,*,workers=2,max_items=6,collector=runtime.collect_registry):
    if not 1<=workers<=2 or not 1<=max_items<=12:
        raise ValueError('Bounded worker limits required')
    with engine.connect() as c:
        batch=c.execute(text("""SELECT engine_version FROM focus_assessment_batches
            WHERE batch_id=:b"""),{'b':batch_id}).first()
        if not batch or batch[0]!=VERSION:
            raise ValueError('Not an isolated L4–L6 batch')
        interrupted=c.execute(text("""SELECT * FROM focus_assessment_items
            WHERE batch_id=:b AND state IN ('RUNNING','FAILED')"""),
            {'b':batch_id}).mappings().all()
    for slot in interrupted:
        state=runtime.status(engine,slot['nct_id'],slot['run_id']) if slot['run_id'] else None
        completed=bool(state and state['status']=='COMPLETED' and state['report'] is not None)
        stale=datetime.fromisoformat(slot['updated_at'])<datetime.now(timezone.utc)-timedelta(minutes=10)
        if completed or (slot['state']=='RUNNING' and stale):
            with engine.begin() as c:
                c.execute(text("""UPDATE focus_assessment_items SET state=:state,error=:error,
                    updated_at=:at WHERE batch_id=:batch AND nct_id=:nct AND level=:level"""),
                    {'state':'COMPLETED' if completed else 'FAILED',
                     'error':None if completed else 'Interrupted worker; retry eligible',
                     'at':runtime.now(),'batch':batch_id,'nct':slot['nct_id'],'level':slot['level']})
    with engine.connect() as c:
        items=c.execute(text("""SELECT nct_id,level FROM focus_assessment_items
            WHERE batch_id=:b AND level BETWEEN 4 AND 6 AND state IN ('PENDING','FAILED')
            AND attempts<2 ORDER BY nct_id,level LIMIT :limit"""),
            {'b':batch_id,'limit':max_items}).all()
    def one(item):
        nct,level=item
        params={'batch':batch_id,'nct':nct,'level':level,'at':runtime.now()}
        with engine.begin() as c:
            claimed=c.execute(text("""UPDATE focus_assessment_items
                SET state='RUNNING',attempts=attempts+1,updated_at=:at
                WHERE batch_id=:batch AND nct_id=:nct AND level=:level
                AND state IN ('PENDING','FAILED') AND attempts<2"""),params).rowcount
        if not claimed:return
        try:
            request=runtime.RunInput(nct=nct,level=level,mode='CURRENT_EVIDENCE',
                                     contract='LEGACY_SOURCE_AUDIT')
            run_id=runtime.create(engine,request)
            with engine.begin() as c:
                c.execute(text("""UPDATE focus_assessment_items SET run_id=:run
                    WHERE batch_id=:batch AND nct_id=:nct AND level=:level"""),
                    {**params,'run':run_id})
            runtime.execute(engine,run_id,collector)
            state=runtime.status(engine,nct,run_id)
            done=state['status']=='COMPLETED' and state['report'] is not None
            status='COMPLETED' if done else 'FAILED'
            error=None if done else state.get('error') or 'Assessment incomplete'
        except Exception:
            status='FAILED'
            error='Assessment failed; inspect owner job logs'
        with engine.begin() as c:
            c.execute(text("""UPDATE focus_assessment_items SET state=:state,error=:error,
                updated_at=:at WHERE batch_id=:batch AND nct_id=:nct AND level=:level"""),
                {**params,'state':status,'error':error,'at':runtime.now()})
    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(one,items))
    return summary(engine)

def summary(engine):
    saved=focus.roster(engine)
    if not saved:
        return {'status':'BLOCKED_NO_RECONCILED_DATABASE_ROSTER','total':None,'trials':[]}
    with engine.connect() as c:
        if not inspect(engine).has_table('focus_assessment_batches'):
            batch=None
        else:
            batch=c.execute(text("""SELECT batch_id FROM focus_assessment_batches
                WHERE roster_id=:r AND engine_version=:v"""),
                {'r':saved['roster_id'],'v':VERSION}).scalar()
        rows=c.execute(text("""SELECT i.*,r.report_json,r.report_hash FROM focus_assessment_items i
            LEFT JOIN assessment_v2_results r ON r.run_id=i.run_id
            WHERE i.batch_id=:b"""),{'b':batch or ''}).mappings().all() if batch else []
    slots={(row['nct_id'],row['level']):dict(row) for row in rows}
    trials=[]
    for member in saved['members']:
        levels={}
        for level in (4,5,6):
            slot=slots.get((member['nct'],level),{})
            report=None
            if slot.get('report_json'):
                report=runtime.verified_report((slot['report_json'],slot['report_hash']))
                if report.get('nct')!=member['nct'] or report.get('level')!=level:
                    raise ValueError('Saved L4–L6 identity mismatch')
            levels[str(level)]={'state':'COMPLETED' if report else slot.get('state','NOT_RUN'),
                'runId':slot.get('run_id'),'error':slot.get('error'),
                'report':({k:report.get(k) for k in ('runId','nct','level','executedAt','score','fdaPrediction','scientificStatus')} if report else None),
                'missingEvidence':[{'id':v['id'],'state':v['state'],'explanation':v['explanation']}
                    for v in report.get('checks',[]) if v['state'] in ('MISSING','CONFLICTING')] if report else []}
        trials.append({**member,'levels':levels})
    return {'status':'EVIDENCE_COVERAGE_ONLY_NOT_VALIDATED_PREDICTION',
        'batchId':batch,'total':len(trials),'trials':trials}

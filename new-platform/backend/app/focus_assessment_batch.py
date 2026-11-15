"""Checkpointed owner FOCUS research; additive tables, immutable result versions.

Membership is a dated imported owner-source reconciliation, not a claim that a
spreadsheet row or source receipt validates clinical scoring or an FDA event.
"""
from concurrent.futures import ThreadPoolExecutor
import json
from datetime import datetime,timezone,timedelta
import re
from uuid import uuid4
from sqlalchemy import text, inspect
from . import assessment_runtime as runtime
from .scientific_trial_assessment import VERSION


def initialize(engine):
    runtime.initialize(engine)
    with engine.begin() as c:
        c.execute(text('''CREATE TABLE IF NOT EXISTS focus_assessment_rosters (
          roster_id TEXT PRIMARY KEY, source_url TEXT NOT NULL, retrieved_at TEXT NOT NULL,
          source_hash TEXT NOT NULL, members_json TEXT NOT NULL, authority_status TEXT NOT NULL)'''))
        if engine.dialect.name=='postgresql':
            exists=c.execute(text("SELECT 1 FROM pg_trigger WHERE tgname='focus_assessment_rosters_immutable'")).scalar()
            if not exists:c.execute(text('CREATE TRIGGER focus_assessment_rosters_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON focus_assessment_rosters FOR EACH STATEMENT EXECUTE FUNCTION assessment_v2_immutable()'))
        else:
            for operation in ('UPDATE','DELETE'):
                c.execute(text(f"CREATE TRIGGER IF NOT EXISTS focus_rosters_{operation.lower()} BEFORE {operation} ON focus_assessment_rosters BEGIN SELECT RAISE(ABORT, 'FOCUS roster versions are append-only'); END"))
        c.execute(text('''CREATE TABLE IF NOT EXISTS focus_assessment_batches (
          batch_id TEXT PRIMARY KEY, roster_id TEXT NOT NULL, engine_version TEXT NOT NULL,
          created_at TEXT NOT NULL, UNIQUE(roster_id,engine_version))'''))
        c.execute(text('''CREATE TABLE IF NOT EXISTS focus_assessment_items (
          batch_id TEXT NOT NULL,nct_id TEXT NOT NULL,level INTEGER NOT NULL,
          state TEXT NOT NULL,attempts INTEGER NOT NULL,run_id TEXT,error TEXT,updated_at TEXT NOT NULL,
          PRIMARY KEY(batch_id,nct_id,level))'''))


def import_roster(engine,document):
    """Trusted operator import only. Never exposed as a browser evidence endpoint."""
    members=document['members'];seen=set()
    if not members or len(members)>500:raise ValueError('Empty or oversized FOCUS roster')
    for row in members:
        if not re.fullmatch(r'NCT[0-9]{8}',row.get('nct','')) or row['nct'] in seen:raise ValueError('Invalid/duplicate exact FOCUS NCT')
        if not row.get('company') or not row.get('ticker'):raise ValueError('Missing owner roster identity')
        seen.add(row['nct'])
    if document['sourceUrl']!='https://docs.google.com/spreadsheets/d/1erY_z62b4mHhx5s_3HgJxXoJEslbLngMuQNfhcuSviU/edit#gid=202611061':raise ValueError('Unapproved owner roster source')
    from .scientific_trial_assessment import instant
    instant(document['retrievedAt'])
    digest=runtime.sha(document);initialize(engine)
    with engine.begin() as c:
        c.execute(text('''INSERT INTO focus_assessment_rosters VALUES(:id,:url,:at,:hash,:members,:authority)
          ON CONFLICT(roster_id) DO NOTHING'''),{'id':digest,'url':document['sourceUrl'],'at':document['retrievedAt'],'hash':digest,
          'members':runtime.packed(members),'authority':'OWNER_SHEET_RECONCILED_DATABASE_SNAPSHOT'})
    return digest


def roster(engine):
    if not inspect(engine).has_table('focus_assessment_rosters'):return None
    with engine.connect() as c:
        row=c.execute(text('SELECT * FROM focus_assessment_rosters ORDER BY retrieved_at DESC,roster_id DESC LIMIT 1')).mappings().first()
    if not row:return None
    members=json.loads(row['members_json'])
    if runtime.sha({'sourceUrl':row['source_url'],'retrievedAt':row['retrieved_at'],'members':members})!=row['source_hash']:
        raise ValueError('FOCUS roster integrity mismatch')
    return {**dict(row),'members':members}


def create(engine):
    initialize(engine);saved=roster(engine)
    if not saved:raise ValueError('NO_RECONCILED_FOCUS_DATABASE_ROSTER: import a verified current owner roster first')
    with engine.begin() as c:
        c.execute(text('''INSERT INTO focus_assessment_batches VALUES(:id,:roster,:version,:at)
          ON CONFLICT(roster_id,engine_version) DO NOTHING'''),{'id':str(uuid4()),'roster':saved['roster_id'],'version':VERSION,'at':runtime.now()})
        batch=c.execute(text('SELECT batch_id FROM focus_assessment_batches WHERE roster_id=:r AND engine_version=:v'),{'r':saved['roster_id'],'v':VERSION}).scalar_one()
        for row in saved['members']:
            for level in (1,2,3):
                c.execute(text('''INSERT INTO focus_assessment_items VALUES(:batch,:nct,:level,'PENDING',0,NULL,NULL,:at)
                  ON CONFLICT(batch_id,nct_id,level) DO NOTHING'''),{'batch':batch,'nct':row['nct'],'level':level,'at':runtime.now()})
    return batch


def execute(engine,batch_id,*,workers=2,max_items=6,collector=runtime.collect_registry):
    """Each invocation is bounded; checkpoints resume without replacing results.

    Conditional row claim prevents concurrent batch invocations executing a slot
    twice. Failed slots get at most two attempts. Exhausted slots remain visible.
    """
    if not 1<=workers<=2 or not 1<=max_items<=12:raise ValueError('Bounded batch limits required')
    # Recover the save/checkpoint gap before claiming a retry. A completed
    # immutable result is never recomputed merely because the worker stopped.
    with engine.connect() as c:
        interrupted=c.execute(text("SELECT * FROM focus_assessment_items WHERE batch_id=:id AND state IN ('RUNNING','FAILED') AND run_id IS NOT NULL"),{'id':batch_id}).mappings().all()
    for slot in interrupted:
        state=runtime.status(engine,slot['nct_id'],slot['run_id'])
        completed=state['status']=='COMPLETED' and state['report'] is not None
        stale=datetime.fromisoformat(slot['updated_at'])<datetime.now(timezone.utc)-timedelta(minutes=10)
        if completed or (slot['state']=='RUNNING' and stale):
            with engine.begin() as c:c.execute(text('UPDATE focus_assessment_items SET state=:state,error=:error,updated_at=:at WHERE batch_id=:batch AND nct_id=:nct AND level=:level'),
              {'state':'COMPLETED' if completed else 'FAILED','error':None if completed else 'Interrupted worker; safe bounded retry eligible','at':runtime.now(),'batch':batch_id,'nct':slot['nct_id'],'level':slot['level']})
    with engine.connect() as c:
        items=c.execute(text('''SELECT nct_id,level FROM focus_assessment_items WHERE batch_id=:id
          AND state IN ('PENDING','FAILED') AND attempts<2 ORDER BY nct_id,level LIMIT :limit'''),{'id':batch_id,'limit':max_items}).all()
    def one(item):
        nct,level=item;params={'batch':batch_id,'nct':nct,'level':level,'at':runtime.now()}
        with engine.begin() as c:
            claimed=c.execute(text('''UPDATE focus_assessment_items SET state='RUNNING',attempts=attempts+1,updated_at=:at
              WHERE batch_id=:batch AND nct_id=:nct AND level=:level AND state IN ('PENDING','FAILED') AND attempts<2'''),params).rowcount
        if not claimed:return
        try:
            q=runtime.RunInput(nct=nct,level=level,mode='CURRENT_EVIDENCE',contract='SCIENTIFIC_1_3')
            run=runtime.create(engine,q)
            with engine.begin() as c:c.execute(text('UPDATE focus_assessment_items SET run_id=:run WHERE batch_id=:batch AND nct_id=:nct AND level=:level'),{**params,'run':run})
            runtime.execute(engine,run,collector)
            state=runtime.status(engine,nct,run)
            status='COMPLETED' if state['status']=='COMPLETED' and state['report'] else 'FAILED'
            error=state['error']
        except Exception as exc:
            status='FAILED';error=str(exc) if isinstance(exc,ValueError) else 'Batch assessment failed; inspect owner job log'
        with engine.begin() as c:c.execute(text('''UPDATE focus_assessment_items SET state=:state,error=:error,updated_at=:at
          WHERE batch_id=:batch AND nct_id=:nct AND level=:level'''),{**params,'state':status,'error':error,'at':runtime.now()})
    with ThreadPoolExecutor(max_workers=workers) as pool:list(pool.map(one,items))
    return summary(engine)


def summary(engine):
    saved=roster(engine)
    # A whole-list request freezes the exact server inventory without changing
    # owner-sheet membership. Reuse that dated manifest for shared result reads
    # when no separately reconciled live-sheet database roster exists.
    if not saved and inspect(engine).has_table('assessment_cohort_batches'):
        with engine.connect() as c:
            manifests=c.execute(text('SELECT manifest_json,manifest_hash,created_at FROM assessment_cohort_batches ORDER BY created_at DESC,batch_id DESC LIMIT 100')).mappings().all()
        for row in manifests:
            manifest=json.loads(row['manifest_json'])
            if manifest['population']!='FOCUS' or manifest['scope']!='all':continue
            if runtime.sha(manifest)!=row['manifest_hash']:raise ValueError('FOCUS batch inventory integrity failure')
            source=manifest['source']
            saved={'members':manifest['records'],'roster_id':row['manifest_hash'],
                   'source_url':source['source'],'retrieved_at':source.get('asOf',row['created_at']),
                   'source_hash':row['manifest_hash'],'authority_status':source['status']}
            break
    if not saved:return {'status':'BLOCKED_NO_RECONCILED_DATABASE_ROSTER','total':None,'trials':[],'counts':{},'source':None}
    batch=None;slots={};latest={}
    if inspect(engine).has_table('focus_assessment_batches'):
        with engine.connect() as c:
            batch=c.execute(text('SELECT batch_id FROM focus_assessment_batches WHERE roster_id=:r AND engine_version=:v'),{'r':saved['roster_id'],'v':VERSION}).scalar()
            if batch:
                slots={(row['nct_id'],row['level']):dict(row) for row in c.execute(text('SELECT i.*,r.report_json,r.report_hash FROM focus_assessment_items i LEFT JOIN assessment_v2_results r ON r.run_id=i.run_id WHERE i.batch_id=:b'),{'b':batch}).mappings()}
    if inspect(engine).has_table('assessment_v2_results'):
        # Both tabs select the same latest source-bound CURRENT result, including
        # later individual runs. Batch checkpoints retain their original run IDs.
        names=','.join(':n'+str(i) for i in range(len(saved['members'])))
        params={'version':VERSION+'/level-%',**{'n'+str(i):m['nct'] for i,m in enumerate(saved['members'])}}
        with engine.connect() as c:
            rows=c.execute(text('SELECT nct_id,level,report_json,report_hash FROM (SELECT nct_id,level,report_json,report_hash,ROW_NUMBER() OVER (PARTITION BY nct_id,level ORDER BY created_at DESC,run_id DESC) AS position FROM assessment_v2_results WHERE mode=\'CURRENT_EVIDENCE\' AND engine_version LIKE :version AND nct_id IN ('+names+')) ranked WHERE position=1'),params).mappings()
            latest={(row['nct_id'],row['level']):dict(row) for row in rows}
    trials=[];counts={str(level):{'processed':0,'scored':0,'incomplete':0,'failed':0} for level in (1,2,3)};fully=0
    for member in saved['members']:
        levels={}
        for level in (1,2,3):
            slot=slots.get((member['nct'],level),{});report=None
            selected=latest.get((member['nct'],level),slot)
            if selected.get('report_json'):
                report=runtime.verified_report((selected['report_json'],selected['report_hash']))
                if report.get('contract')!='SCIENTIFIC_1_3':raise ValueError('FOCUS scientific contract mismatch')
                if report['nct']!=member['nct'] or report['level']!=level:raise ValueError('FOCUS saved assessment identity mismatch')
            gaps=[]
            if report:
                gaps=[x for x in report['checks'] if x['state'] in {'MISSING','UNVERIFIED','CONCERNS','NOT_ASSESSED','BLOCKED_UNVERIFIED_PHASE'}]
                counts[str(level)]['processed']+=1
                counts[str(level)]['scored']+=int(report['score']['value'] is not None and report['score']['kind']!='LEVEL_SPECIFIC_EVIDENCE_COVERAGE')
                counts[str(level)]['incomplete']+=int(bool(gaps) or report['score']['kind']=='NOT_VALIDATED')
            elif slot.get('state')=='FAILED':counts[str(level)]['failed']+=1
            levels[str(level)]={'state':'COMPLETED' if report else slot.get('state','NOT_RUN'),'runId':report['runId'] if report else slot.get('run_id'),'attempts':slot.get('attempts',0),
               'error':slot.get('error'),'report':({k:report[k] for k in ('runId','nct','level','mode','engineVersion','executedAt','executionStatus','scientificStatus','score','fdaPrediction','trialIdentity','context')} if report else None),'missingEvidence':[{'id':x['id'],'state':x['state'],'explanation':x['explanation']} for x in gaps]}
        fully+=int(all(levels[str(l)]['report'] is not None for l in (1,2,3)))
        trials.append({**member,'levels':levels})
    return {'status':'DATABASE_SAVED_RECONCILED_OWNER_ROSTER','batchId':batch,'total':len(trials),'fullyProcessed':fully,
      'counts':counts,'trials':trials,'source':{k:saved[k] for k in ('roster_id','source_url','retrieved_at','source_hash','authority_status')},
      'scoringStatus':'NO_VALIDATED_NUMERICAL_LEVEL_1_3_SPECIFICATION','predictionStatus':'ABSTAIN'}

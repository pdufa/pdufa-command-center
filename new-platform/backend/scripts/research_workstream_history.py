"""Append-only, hash-linked research snapshots; never a clinical/prediction writer.

Each independent workflow carries its previous chain in its own immutable artifact.
A source change requests review; it is not automatically a material scientific
change or permission to replace an authorized grade.
"""
from __future__ import annotations
import argparse, hashlib, json
from datetime import datetime, timezone
from pathlib import Path

SCHEMA='MAIN_INDEPENDENT_RESEARCH_HISTORY_V1'
SCHEMAS={'A':'MAIN_R47_FOCUS_29_RESEARCH_CHECKPOINT',
         'B':'MAIN_R47_HISTORICAL_SOURCE_BUILD_CHECKPOINT'}

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def _time(value):
    if not isinstance(value,str):raise ValueError('HISTORY_TIMESTAMP_REQUIRED')
    when=datetime.fromisoformat(value.replace('Z','+00:00'))
    if when.tzinfo is None:raise ValueError('HISTORY_TIMEZONE_REQUIRED')
    return when.astimezone(timezone.utc)

def _closed_snapshot(snapshot,track):
    if track not in SCHEMAS or not isinstance(snapshot,dict) or snapshot.get('schema')!=SCHEMAS[track]:
        raise ValueError('CROSS_TRACK_OR_INVALID_CHECKPOINT')
    if snapshot.get('productionWriteAuthorized') is not False or snapshot.get('modelTrainingAuthorized') is not False:
        raise ValueError('RESEARCH_HISTORY_CANNOT_AUTHORIZE_RELEASE')
    if track=='A':
        if (snapshot.get('independentlyVerifiedScientificGrades')!=0 or snapshot.get('validatedFdaApplicationForecasts')!=0
                or snapshot.get('calibratedAccuracy') is not None or snapshot.get('probabilityOrCertainty') is not None
                or snapshot.get('officialFDAOutcomeForecast')!='ABSTAIN'):
            raise ValueError('UNVERIFIED_PREDICTION_HISTORY')
        apps=snapshot.get('applicationResearchRecords')
        if not isinstance(apps,list) or len(apps)!=23 or len({r.get('applicationCycleId') for r in apps})!=23:
            raise ValueError('EXACT_APPLICATION_RESEARCH_HISTORY_REQUIRED')
        if any(r.get('numericalProbability') is not None or r.get('independentReviewerSigned') is not False or
               r.get('prediction') not in ('ABSTAIN','NOT_APPLICABLE_ALREADY_OBSERVED_IN_SNAPSHOT') or
               r.get('reviewDelayPrediction') not in ('ABSTAIN','NOT_APPLICABLE_ALREADY_OBSERVED_IN_SNAPSHOT') for r in apps):
            raise ValueError('UNVERIFIED_APPLICATION_FORECAST_IN_HISTORY')
    elif (snapshot.get('pairedIndependentHistory')!=0 or snapshot.get('prospectiveAccuracy') is not None or
          snapshot.get('calibration') is not None or snapshot.get('approvalProbability') is not None):
        raise ValueError('UNVERIFIED_BACKTEST_HISTORY')


def validate_history(history,track):
    if track not in SCHEMAS or not isinstance(history,dict) or set(history)!={'schema','track','events','headSha256'} or history['schema']!=SCHEMA or history['track']!=track:
        raise ValueError('CROSS_TRACK_OR_INVALID_HISTORY')
    events=history['events']
    if not isinstance(events,list) or len(events)>1000:raise ValueError('HISTORY_CAPACITY_REQUIRES_DURABLE_ARCHIVE')
    previous=None;at=None;identities=set()
    for i,event in enumerate(events,1):
        if not isinstance(event,dict) or set(event)!={'revision','previousSha256','snapshotSha256','recordedAtUtc','runId','commit','snapshot','sha256'}:
            raise ValueError('INVALID_RESEARCH_HISTORY_EVENT')
        _closed_snapshot(event['snapshot'],track)
        if (type(event['revision']) is not int or not isinstance(event['runId'],str) or not event['runId'].isdigit()
                or not isinstance(event['commit'],str) or len(event['commit'])!=40 or any(c not in '0123456789abcdef' for c in event['commit'])):
            raise ValueError('INVALID_RESEARCH_HISTORY_IDENTITY')
        payload={k:v for k,v in event.items() if k!='sha256'}
        if (event['revision']!=i or event['previousSha256']!=previous or
            event['snapshotSha256']!=digest(event['snapshot']) or event['sha256']!=digest(payload)):
            raise ValueError('RESEARCH_HISTORY_DIGEST_OR_SEQUENCE_MISMATCH')
        when=_time(event['recordedAtUtc'])
        if at is not None and when<at:raise ValueError('RESEARCH_HISTORY_TIME_REGRESSION')
        key=(event['runId'],event['commit'])
        if key in identities:raise ValueError('DUPLICATED_RESEARCH_RUN_IDENTITY')
        identities.add(key);previous=event['sha256'];at=when
    if previous!=history['headSha256']:raise ValueError('RESEARCH_HISTORY_HEAD_MISMATCH')
    return history

def append_snapshot(history,snapshot,*,track,at,run_id,commit):
    _closed_snapshot(snapshot,track)
    if not isinstance(run_id,str) or not run_id.isdigit() or not isinstance(commit,str) or len(commit)!=40 or any(c not in '0123456789abcdef' for c in commit):
        raise ValueError('REAL_WORKFLOW_RUN_AND_COMMIT_REQUIRED')
    now=_time(at)
    old={'schema':SCHEMA,'track':track,'events':[],'headSha256':None} if history is None else validate_history(history,track)
    # JSON roundtrip avoids mutating caller-owned previous history or snapshots.
    events=json.loads(json.dumps(old['events']))
    for event in events:
        if event['runId']==run_id:
            if event['commit']!=commit or event['snapshotSha256']!=digest(snapshot):raise ValueError('RESEARCH_RUN_REPLAY_CONFLICT')
            return old
    if events and now<_time(events[-1]['recordedAtUtc']):raise ValueError('RESEARCH_HISTORY_TIME_REGRESSION')
    if len(events)>=1000:raise ValueError('HISTORY_CAPACITY_REQUIRES_DURABLE_ARCHIVE')
    event={'revision':len(events)+1,'previousSha256':old['headSha256'],
           'snapshotSha256':digest(snapshot),'recordedAtUtc':at,'runId':run_id,
           'commit':commit,'snapshot':json.loads(json.dumps(snapshot))}
    event['sha256']=digest(event);events.append(event)
    return validate_history({'schema':SCHEMA,'track':track,'events':events,'headSha256':event['sha256']},track)

def changed_applications(previous,current):
    """Separate proved byte-version changes from temporary access changes."""
    def versions(case):
        found={}
        for row in case.get('sourceVersions',{}).get('trials',[]):
            for kind,sha in row['sourceVersions'].items():
                if sha is not None:found[row['nct']+':'+kind]=sha
        for source in case.get('applicationSourceReferences',[]):
            if source.get('sha256') is not None:found[source['url']]=source['sha256']
        return found
    old={r['applicationCycleId']:r for r in (previous or {}).get('applicationResearchRecords',[])}
    out=[]
    for case in current.get('applicationResearchRecords',[]):
        before=old.get(case['applicationCycleId'])
        changed=before is not None and before['evidenceFingerprint']!=case['evidenceFingerprint']
        version_change=False
        if before is not None:
            prior,latest=versions(before),versions(case)
            version_change=any(prior[k]!=latest[k] for k in prior.keys() & latest.keys())
        state=('INITIAL_REVIEW_REQUIRED' if before is None else 'SOURCE_VERSION_CHANGED_REVIEW_REQUIRED' if version_change
               else 'SOURCE_AVAILABILITY_CHANGED_REVIEW_REQUIRED' if changed else 'SOURCE_VERSIONS_UNCHANGED')
        out.append({'applicationCycleId':case['applicationCycleId'],'state':state,
          'materialScientificChangeAdjudicated':False,'reassessmentRequired':changed,
          'priorResearchRecord':before,'currentResearchRecord':case,
          'authorizedGradesOrPredictionsModified':False})
    return out

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--track',choices=['A','B'],required=True)
    p.add_argument('--snapshot',type=Path,required=True);p.add_argument('--previous',type=Path)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--run-id',required=True);p.add_argument('--commit',required=True)
    a=p.parse_args()
    if a.output.exists() or a.output.is_symlink() or not a.output.parent.is_dir():raise ValueError('WRITE_ONCE_HISTORY_PATH_REQUIRED')
    def read(path):
        if path.is_symlink() or not path.is_file() or path.stat().st_size>32_000_000:raise ValueError('UNSAFE_HISTORY_INPUT')
        return json.loads(path.read_bytes())
    old=read(a.previous) if a.previous else None;current=read(a.snapshot)
    history=append_snapshot(old,current,track=a.track,at=datetime.now(timezone.utc).isoformat(),run_id=a.run_id,commit=a.commit)
    out={'history':history,'reassessment':changed_applications(old['events'][-1]['snapshot'] if old and old['events'] else None,current) if a.track=='A' else [],
         'clinicalWrites':0,'predictionReleaseAuthorized':False}
    # Keep the chain itself independently loadable on the next execution.
    with a.output.open('x') as f:json.dump(history,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
    with a.output.with_name('reassessment.json').open('x') as f:json.dump({k:v for k,v in out.items() if k!='history'},f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps({'track':a.track,'historyRevisions':len(history['events']),'headSha256':history['headSha256'],'sourceChangedApplications':sum(r['reassessmentRequired'] for r in out['reassessment']),'clinicalWrites':0}))
if __name__=='__main__':main()

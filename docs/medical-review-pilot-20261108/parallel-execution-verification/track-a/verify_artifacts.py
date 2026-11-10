"""Read-only validation of actual Track A run42678294690 artifact contents.

Supply downloaded original ZIPs; no network request, extraction or clinical write.
"""
from __future__ import annotations
import argparse,hashlib,json,sys,zipfile
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'new-platform/backend'))
from scripts.build_focus_research_checkpoint_r47 import collect,canonical_manifest
from scripts.research_workstream_history import validate_history

EXPECTED={
 'source':'e9962faad6974121a535aa8bd7699ac2131c59bad88d1c08f455e85e0a4f1664',
 'history':'efb3043cf290d18a11747186a1f5129e2e9de4fe53527651e72040143b1c8c6c'}

def verify(source_path,history_path):
    for kind,path in [('source',source_path),('history',history_path)]:
        assert hashlib.sha256(path.read_bytes()).hexdigest()==EXPECTED[kind],kind+' GitHub artifact digest mismatch'
    checks=0
    with zipfile.ZipFile(source_path) as sources,zipfile.ZipFile(history_path) as history_zip:
        report=json.loads(sources.read('evidence_readiness.json'))
        apps=json.loads(sources.read('applications.json'))
        inputs={};digests={}
        for kind,folder in [('primary','primary-original'),('safety','safety-original'),('documents','docs-original')]:
            raw=sources.read(kind+'.json');digests[kind]=hashlib.sha256(raw).hexdigest();inputs[kind]=json.loads(raw)
            assert digests[kind]==report['sourceReceiptSha256'][kind]
            for row in inputs[kind]['records']:
                if row.get('sourceResponseSha256'):
                    raw=sources.read(folder+'/'+row['nct']+'.json')
                    assert hashlib.sha256(raw).hexdigest()==row['sourceResponseSha256']
                    assert json.loads(raw)['protocolSection']['identificationModule']['nctId']==row['nct']
                    checks+=1
        assert report==collect(inputs,digests,report['generatedAtUtc'],apps)
        manifest=canonical_manifest();expected={r['nct'] for r in manifest['trialRows']}
        assert {r['nct'] for r in report['rows']}==expected
        assert {a['applicationCycleId'] for a in report['applicationResearchRecords']}=={g['cycleId'] for g in manifest['applicationGroups']}
        assert len(report['rows'])==29 and len(report['applicationResearchRecords'])==23
        assert report['validatedFdaApplicationForecasts']==report['independentlyVerifiedScientificGrades']==0
        assert report['newScientificallyQualifiedResearchPredictions']==0
        assert report['calibratedAccuracy'] is None and report['probabilityOrCertainty'] is None
        all_sources={};fda=[]
        for case in apps['applicationGroups']:
            refs=[case.get('applicationSource'),case.get('alternateOfficialSecSource')]+case.get('additionalOfficialFdaSources',[])
            for source in refs:
                if not source:continue
                all_sources[source['url']]=source
                if source['status']=='FETCHED':
                    raw=sources.read('application-original/'+source['rawArtifact'])
                    assert len(raw)==source['bytes']
                    assert hashlib.sha256(raw).hexdigest()==source['sha256']
                    assert source['sourceBodyPreserved'] is True
                    checks+=1
                    if source.get('sourceRole'):
                        assert raw.startswith(b'%PDF-')
                        fda.append({'applicationCycleId':case['cycleId'],'url':source['url'],'bytes':len(raw),'sha256':source['sha256'],'pdfMagicVerified':True,'role':source['sourceRole']})
        history=json.loads(history_zip.read('research-history.json'))
        validate_history(history,'A')
        assert len(history['events'])==1 and history['events'][0]['snapshot']==report
        assert history['events'][0]['runId']=='42678294690'
        assert history['events'][0]['commit']=='f42605f7228960386e7fce207327c7a996391cb7'
        assert json.loads(sources.read('history/research-history.json'))==history
        assessment=json.loads(history_zip.read('reassessment.json'))
        assert assessment['clinicalWrites']==0 and assessment['predictionReleaseAuthorized'] is False
        assert len(assessment['reassessment'])==23
        return {
          'schema':'MAIN_ACTUAL_TRACK_A_ARTIFACT_VERIFICATION_V1',
          'workflowRunId':42678294690,'jobId':129365556705,'commit':'f42605f7228960386e7fce207327c7a996391cb7',
          'workflowConclusion':'success','jobStartedAtUtc':'2026-11-09T18:54:52Z','jobCompletedAtUtc':'2026-11-09T18:55:22Z',
          'sourceArtifactId':13702050485,'sourceArtifactSha256':EXPECTED['source'],
          'historyArtifactId':13701591373,'historyArtifactSha256':EXPECTED['history'],
          'artifactExpiresAtUtc':'2027-02-07T18:54:49Z','artifactRetentionDays':90,
          'canonicalNcts':29,'canonicalApplicationGroups':23,'applicationResearchRecords':23,
          'predictionStates':dict(Counter(r['prediction'] for r in report['applicationResearchRecords'])),
          'qualifiedScientificPredictions':0,'independentScientificGrades':0,'validatedFdaForecasts':0,
          'registryIdentityAndRawDigestChecks':87,'rawDigestChecksIncludingApplicationReferences':checks,
          'registryRecordsCaptured':apps['clinicalTrialsGovRecordsFetched'],
          'uniqueApplicationSourceUrls':len(all_sources),'applicationSourceStatuses':dict(Counter(s['status'] for s in all_sources.values())),
          'sourceUnavailable':[{'url':s['url'],'httpStatus':s.get('httpStatus')} for s in all_sources.values() if s['status']!='FETCHED'],
          'all23GroupsHaveAtLeastOneRetrievedPublicSource':apps['applicationGroupsWithAvailablePublicSource']==23,
          'nctsWithCurrentPostedPrimaryTables':report['trialsWithCurrentPostedPrimaryTables'],
          'nctsWithCurrentSapAttachmentMetadata':report['trialsWithCurrentRegistrySap'],
          'nctsWithRequiredIndependentEvidenceGaps':report['trialsMissingAnyRequiredIndependentEvidence'],
          'originalFdaPdfBodyCaptures':fda,'historyRevisions':1,'historyHeadSha256':history['headSha256'],
          'reassessmentStates':dict(Counter(x['state'] for x in assessment['reassessment'])),
          'liveHistoryRestoreExercised':False,'liveHistoryRestoreReason':'First history artifact; prior source artifacts preserved. Restore step skipped, not operationally proven by this initial run.',
          'measuredAccuracy':None,'calibration':None,'modelTrainingAuthorized':False,'productionWrites':False,
          'meaning':'Actual public source retrieval and versioned unscored research records; not independently verified clinical or prediction performance.',
          'verification':'PASS'}

def verify_restart(initial_path,restarted_path):
    assert hashlib.sha256(restarted_path.read_bytes()).hexdigest()=='14b4f515fa5ca50792795a94443ccac0cd4bc7ff0c8600f15b4be98e5ea7e414'
    with zipfile.ZipFile(initial_path) as first_zip,zipfile.ZipFile(restarted_path) as second_zip:
        first=json.loads(first_zip.read('research-history.json'))
        second=json.loads(second_zip.read('research-history.json'))
        assessment=json.loads(second_zip.read('reassessment.json'))
    validate_history(second,'A')
    assert len(second['events'])==2 and second['events'][0]==first['events'][0]
    assert second['events'][1]['previousSha256']==first['headSha256']
    assert second['events'][1]['runId']=='42679838862'
    assert assessment['clinicalWrites']==0 and assessment['predictionReleaseAuthorized'] is False
    assert all(r['materialScientificChangeAdjudicated'] is False and r['authorizedGradesOrPredictionsModified'] is False for r in assessment['reassessment'])
    return {'runId':42679838862,'firstEventEntirelyPreserved':True,'priorHeadSha256':first['headSha256'],
            'currentHeadSha256':second['headSha256'],'revisions':2,
            'reassessmentStates':dict(Counter(x['state'] for x in assessment['reassessment'])),
            'clinicalWrites':0,'independentlyAdjudicatedMaterialChanges':0,'verification':'PASS'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--sources',type=Path,required=True);p.add_argument('--history',type=Path,required=True);p.add_argument('--output',type=Path);p.add_argument('--restart-history',type=Path)
    a=p.parse_args();report=verify(a.sources,a.history)
    if a.restart_history:report['restartVerification']=verify_restart(a.history,a.restart_history)
    text=json.dumps(report,indent=2,sort_keys=True)+'\n'
    if a.output:
        with a.output.open('x') as f:f.write(text)
    print(text)
if __name__=='__main__':main()

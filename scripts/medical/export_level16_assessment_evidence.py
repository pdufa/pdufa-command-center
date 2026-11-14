#!/usr/bin/env python3
"""Package existing source-bound owner research for the Next.js assessment runner.

No network, original document bodies, predictions, owner acceptance or third-party
authorization. --check verifies reproducibility against retained research inputs.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
REPORTS=ROOT/'reports/scientific-levels1-6'
OUTPUT=ROOT/'new-platform/frontend/data/level16AssessmentEvidence.json'
SOURCES=['focus-source-research-20261114.json','orca2-owner-research-dossier-20261114-v1.json',
         'orca2-publication-outcomes-20261114.json','orca3-publication-outcomes-20261114.json']


def module(name):
    spec=importlib.util.spec_from_file_location(name,Path(__file__).with_name(name+'.py'))
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result


def build():
    research,dossier,orca2,orca3=[json.loads((REPORTS/name).read_text(encoding='utf-8')) for name in SOURCES]
    prep=module('level16_research_preparation')
    roster=json.loads(prep.ROSTER.read_text(encoding='utf-8'))
    ncts=[r['nct'] for r in roster['records']]
    prep.validate_snapshot(research,ncts)
    module('level16_scientific_coverage').coverage(research)
    module('level16_orca2_owner_dossier').validate_packet(dossier,ncts)
    publications={}
    for name,doc in [('level16_orca2_publication_review',orca2),('level16_orca3_publication_review',orca3)]:
        publications[doc['nct']]=module(name).assess(doc)
    owner_question=module('level16_review_handoff')._owner_question
    rows=[]
    for trial in research['trials']:
        source=trial['registrySource'];nct=trial['nct']
        docs=trial.get('additionalOriginalDocuments',[])
        levels=[]
        source_refs={source['sourceUrl']:{'url':source['sourceUrl'],'date':source['registryPostedVersionDateUnreviewed'],
            'digest':source['documentSha256'],'kind':'REGISTRY'}}
        for doc in docs:
            source_refs[doc['sourceUrl']]={'url':doc['sourceUrl'],'date':doc.get('registryDeclaredDocumentDateUnreviewed'),
                'digest':doc['documentSha256'],'kind':doc['sourceKind']}
        if nct==dossier['nct']:
            for item in dossier['sourceInventory']:
                receipt=item['receipt'];source_refs[receipt['sourceUrl']]={'url':receipt['sourceUrl'],
                    'date':item.get('documentDate') or item.get('publicationDate') or item.get('dateText'),
                    'digest':receipt['documentSha256'],'kind':item['sourceKind']}
        # Bind each quantitative publication extraction to its retained original
        # full-text receipt, rather than attributing publication numbers to a registry.
        comparison_source = None
        publication_doc = {orca2['nct']: orca2, orca3['nct']: orca3}.get(nct)
        if publication_doc:
            pmid = publication_doc['source']['pmid']
            publication = next((p for p in trial.get('publicationResearch', [])
                                if p['pmid'] == pmid and nct in p['indexedNctsUnreviewed']), None)
            receipt = publication.get('fullTextReceipt') if publication else None
            if receipt and receipt.get('boundPmidUnreviewed') != pmid:
                raise ValueError('Publication receipt identity mismatch')
            if not receipt and nct == dossier['nct']:
                original = next((s for s in dossier['sourceInventory']
                    if s['nct'] == nct and s['receipt']['sourceUrl'] == publication_doc['source']['url']), None)
                receipt = original['receipt'] if original else None
            if publication and receipt:
                comparison_source = {'nct': nct, 'pmid': pmid,
                    'endpointDomain': 'CO_VERIFIED_SMOKING_ABSTINENCE',
                    'sourceUrl': receipt['sourceUrl'], 'retrievedAt': receipt['retrievedAt'],
                    'publicationDate': (publication_doc['source'].get('publicationDate') or publication_doc['source']['publishedDate']),
                    'indexedPublicationDate': publication['publicationDate'],
                    'documentSha256': receipt['documentSha256']}
                source_refs[receipt['sourceUrl']] = {'url': receipt['sourceUrl'],
                    'date': (publication_doc['source'].get('publicationDate') or publication_doc['source']['publishedDate']), 'digest': receipt['documentSha256'],
                    'kind': 'PUBLICATION_FULL_TEXT'}
        for item in trial['levels']:
            number=item['level']
            facts=[{'text':f['finding'],'value':f['sourceValue'],'locator':f['locator'],'sourceUrl':f['sourceUrl']}
                   for f in item['preliminaryFindings']]
            interpretation=item['preliminaryResearchInterpretation'];questions=item['questions']
            reasons=item['supportingReasons'];limitations=item['limitations']+item['riskFactorsRequiringReview']
            contradictions=item['contradictoryFindings']
            if nct==dossier['nct']:
                original=dossier['levels'][number-1]
                refs={s['id']:s['receipt']['sourceUrl'] for s in dossier['sourceInventory']}
                facts += [{'text':f['observation'],'value':None,'locator':f['locator'],
                           'sourceUrl':refs[f['sourceIds'][0]]} for f in original['factualObservations']]
                interpretation=original['preliminaryInterpretation'];questions=original['ownerCheckQuestions']
                reasons=original['supportingReasons'];limitations=original['risksAndLimitations']
                contradictions=original['contradictoryEvidence']
            literature=item.get('publicLiteratureObservationUnreviewed')
            if literature:
                facts.append({'text':literature['factualObservation'],'value':None,'locator':literature['batchLocator'],
                              'sourceUrl':literature['sourceUrl']})
                source_refs[literature['sourceUrl']]={'url':literature['sourceUrl'],
                    'date':literature['publicationDateUnreviewed'],'digest':literature['documentSha256'],
                    'kind':'PUBLICATION_ABSTRACT_RECORD'}
            levels.append({'level':number,'facts':facts,'interpretation':owner_question(interpretation),
                'reasons':[owner_question(x) for x in reasons],
                'questions':[owner_question(x) for x in questions],
                'limitations':[owner_question(x) for x in limitations],
                'contradictions':[owner_question(x) for x in contradictions],
                'notYetExpected':item['notYetExpectedEvidence']})
        rows.append({'nct':nct,'ticker':trial['ticker'],'company':trial['company'],
            'indications':source['indicationsUnreviewed'],'population':source['populationUnreviewed'],
            'phases':source['phasesUnreviewed'],'registryStatus':source['studyStatusUnreviewed'],
            'registryUrl':source['sourceUrl'],'registryDigest':source['documentSha256'],
            'registryVersionDate':source['registryPostedVersionDateUnreviewed'],'retrievedAt':source['retrievedAt'],
            'applicationMappingStatus':trial['mappingStatus'],
            'provisionalApplicationCycleIds':trial['candidateApplicationCycleIdsUnverified'],
            'protocolCollected':any(d['sourceKind'] in ('PROTOCOL','PROTOCOL_AND_SAP') for d in docs),
            'sapCollected':any(d['sourceKind'] in ('STATISTICAL_ANALYSIS_PLAN','PROTOCOL_AND_SAP') for d in docs),
            'registryResultsPresent':source['registryResultsContentPresent'],
            'reportedClinicalResultsPresent':bool(source['primaryResultsUnreviewed']) or any(l.get('publicLiteratureObservationUnreviewed') for l in trial['levels']),
            'design':source['designUnreviewed'],'primaryEndpoints':source['primaryEndpointsUnreviewed'],
            'sources':list(source_refs.values()),'levels':levels,
            'reportedComparisons':[(c if 'activeAbstinent' in c else {
                'id':c['id'],'classification':c['type'],'arm':c['arm'],'interval':c['period'],
                'activeAbstinent':c['activeCount'],'activeRandomized':c['activeDenom'],'activePct':c['activePercent'],
                'placeboAbstinent':c['placeboCount'],'placeboRandomized':c['placeboDenom'],'placeboPct':c['placeboPercent'],
                'oddsRatioReported':c['publishedOddsRatio'],'ci95Reported':c['table95ci'],
                'pValueReported':c['publishedPValue'],'locator':c['locator']})
                for c in publications.get(nct,{}).get('publishedEfficacyComparisons',[])],
            'publishedComparisonSource':comparison_source,
            'publishedSafety':publications.get(nct,{}).get('publishedSafetyObservation'),
            'statisticalChronology':dossier['chronologyReconciliation'] if nct==dossier['nct'] else None})
    return {'schemaVersion':1,'kind':'FOCUS_LEVEL16_COLLECTED_EVIDENCE_OWNER_RESEARCH',
        'evidenceCutoffDate':research['evidenceCutoffDate'],'rosterAsOf':roster['asOf'],
        'sourceSnapshotDigests':{name:hashlib.sha256((REPORTS/name).read_bytes()).hexdigest() for name in SOURCES},
        'historicalPredictionInputPermitted':False,'ownerReviewStatus':'OWNER_NOT_REVIEWED',
        'externalVerificationRequired':False,'trials':rows}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args()
    raw=json.dumps(build(),ensure_ascii=False,indent=2)+'\n'
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding='utf-8')!=raw:raise SystemExit('Packaged Level 1–6 evidence is stale; regenerate from retained sources')
        print('Packaged Level 1–6 evidence matches all retained source inputs')
    else:OUTPUT.write_text(raw,encoding='utf-8');print(OUTPUT)


if __name__=='__main__':main()

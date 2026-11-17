#!/usr/bin/env python3
"""Exact-FOCUS registered/posted primary crosswalk, source-only and abstaining."""
import argparse
from collections import Counter
import hashlib
import json
import posixpath
from pathlib import Path
import re
import zipfile

NCT = re.compile(r"NCT[0-9]{8}\Z")
DIGEST = re.compile(r"[0-9a-f]{64}\Z")


def canonical_sha(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False,
                                     separators=(',', ':')).encode()).hexdigest()


def norm(s):
    return ' '.join(s.split()).casefold() if isinstance(s, str) else ''


def safety_measure(title):
    return any(x in norm(title) for x in (
        'adverse event', 'adverse reaction', 'treatment-emergent',
        'treatment emergent', 'serious adverse'))


class OriginalPackets:
    def __init__(self, source):
        self.root = Path(source).resolve()
        self.z = None

    def __enter__(self):
        if self.root.is_dir():
            return self
        if not zipfile.is_zipfile(self.root):
            raise ValueError('Original registry source is neither extracted directory nor ZIP')
        self.z = zipfile.ZipFile(self.root, 'r')
        return self

    def __exit__(self, *args):
        if self.z:
            self.z.close()

    def read(self, relative):
        if (not isinstance(relative, str) or relative.startswith('/')
                or posixpath.normpath(relative) != relative
                or '..' in relative.split('/')):
            raise ValueError('Unsafe original-source path')
        if self.z:
            return self.z.read(relative)
        dest = (self.root / relative).resolve()
        if not dest.is_relative_to(self.root):
            raise ValueError('Original-source path escaped archive')
        return dest.read_bytes()


def crosswalk(original_registry, review_queue, *,
              expected_trials=32, expected_registered=53,
              expected_posted=16, expected_posted_trials=12):
    if review_queue.get('kind') != 'FOCUS_32_EXACT_NCT_SOURCE_REVIEW_QUEUE_NOT_A_PREDICTION':
        raise ValueError('Expected exact 32-FOCUS source-only queue')
    rows = review_queue.get('trials')
    if not isinstance(rows, list) or len(rows) != expected_trials:
        raise ValueError('Source queue trial count changed')
    ncts = [x.get('nctId') for x in rows]
    if len(set(ncts)) != expected_trials or any(
            not isinstance(x, str) or not NCT.fullmatch(x) for x in ncts):
        raise ValueError('Duplicate/malformed exact FOCUS NCT')
    if (review_queue.get('counts', {}).get('scientificReviewsCompleted') != 0 or
            review_queue.get('counts', {}).get('fdaPredictionsComputed') != 0):
        raise ValueError('Unverified review or forecast was promoted')
    totals, studies = Counter(), []
    with OriginalPackets(original_registry) as src:
        state = json.loads(src.read('ingestion-state.json'))
        for row in rows:
            nct = row['nctId']
            versions = state.get('sources', {}).get(nct, {}).get('versions')
            if not isinstance(versions, list) or not versions:
                raise ValueError('Missing original source receipt: ' + nct)
            version = versions[-1]
            path, digest = version.get('cachePath'), version.get('fingerprint')
            if (not isinstance(path, str) or not path.startswith('registry-cache/')
                    or not isinstance(digest, str) or not DIGEST.fullmatch(digest)):
                raise ValueError('Malformed original source receipt: ' + nct)
            pkt = json.loads(src.read(path))
            if (pkt.get('protocolSection', {}).get('identificationModule', {})
                    .get('nctId') != nct or canonical_sha(pkt) != digest):
                raise ValueError('Wrong original NCT or packet SHA-256: ' + nct)
            if row.get('registryPacketSha256') != digest:
                raise ValueError('Captured source changed since validated review queue')
            registered = (pkt.get('protocolSection', {}).get('outcomesModule', {})
                          .get('primaryOutcomes') or [])
            posted = [o for o in (pkt.get('resultsSection', {})
                       .get('outcomeMeasuresModule', {}).get('outcomeMeasures') or [])
                      if o.get('type') == 'PRIMARY']
            if (len(registered) != row.get('registeredPrimaryOutcomeCount') or
                    len(posted) != row.get('postedPrimaryOutcomeCount')):
                raise ValueError('Primary outcome definition counts changed')
            endpoints = []
            for ix, outcome in enumerate(posted):
                title, frame = outcome.get('title'), outcome.get('timeFrame')
                matching = [i for i, reg in enumerate(registered)
                            if norm(reg.get('measure')) == norm(title)
                            and norm(reg.get('timeFrame')) == norm(frame)]
                if len(matching) > 1:
                    raise ValueError('Duplicate registered endpoint title/time: ' + nct)
                groups = outcome.get('groups') or []
                ids = [g.get('id') for g in groups]
                if None in ids or len(ids) != len(set(ids)):
                    raise ValueError('Missing or duplicate posted arm IDs: ' + nct)
                denominators = outcome.get('denoms') or []
                denominator_ids = sorted({v.get('groupId') for d in denominators
                                         for v in d.get('counts', [])})
                analyses = outcome.get('analyses') or []
                if any(not set(a.get('groupIds', [])).issubset(ids) for a in analyses):
                    raise ValueError('Statistical comparison refers to unknown arm: ' + nct)
                is_safety = safety_measure(title)
                flags = []
                if len(matching) != 1:
                    flags.append('REGISTERED_POSTED_ENDPOINT_MATCH_REVIEW')
                if not ids or not set(ids).issubset(denominator_ids):
                    flags.append('MISSING_ARM_DENOMINATOR_REVIEW')
                if not analyses:
                    flags.append('NO_POSTED_STATISTICAL_COMPARISON_REVIEW_SAP_AND_PUBLICATIONS')
                if is_safety:
                    flags.append('SAFETY_PRIMARY_DO_NOT_RECLASSIFY_AS_EFFICACY')
                if not outcome.get('populationDescription'):
                    flags.append('NO_POSTED_ANALYSIS_POPULATION_DESCRIPTION')
                endpoints.append({
                    'postedMeasureIndex': ix, 'title': title, 'timeFrame': frame,
                    'registeredPrimaryMatch': 'EXACT_TITLE_AND_TIMEFRAME' if len(matching)==1 else 'REVIEW_REQUIRED',
                    'registeredPrimaryIndex': matching[0] if len(matching)==1 else None,
                    'sourceMeasureType': 'SAFETY_TOLERABILITY_PRIMARY' if is_safety else 'NON_SAFETY_PRIMARY_UNADJUDICATED',
                    'populationAsReported': outcome.get('populationDescription'),
                    'unitAsReported': outcome.get('unitOfMeasure'),
                    'paramTypeAsReported': outcome.get('paramType'),
                    'armsAsReported': [{'id': g.get('id'), 'title':g.get('title')} for g in groups],
                    'denominatorGroupIds': denominator_ids,
                    'postedStatisticalComparisonCount': len(analyses),
                    'comparisonsAsPosted': [{
                        'groupIds': a.get('groupIds'),
                        'reportedPValue': a.get('pValue'), 'method':a.get('statisticalMethod'),
                        'hypothesisType': a.get('nonInferiorityType'),
                        'reportedEstimate': a.get('paramValue'),
                        'ciLower':a.get('ciLowerLimit'), 'ciUpper':a.get('ciUpperLimit'),
                        'ciPct':a.get('ciPctValue'),
                        'estimateType':a.get('paramType'),
                    } for a in analyses],
                    'reviewFlags': flags,
                    'clinicalEfficacyIndependentlyAdjudicated': False,
                    'scientificScore': None, 'fdaPrediction': 'ABSTAIN'
                })
                totals['postedPrimaryMeasures'] += 1
                totals['postedSafetyPrimaryMeasures' if is_safety else 'postedNonSafetyPrimaryMeasures'] += 1
                totals['postedWithStatisticalComparisons' if analyses else 'postedWithoutStatisticalComparisons'] += 1
                totals['postedExactRegisteredMatch' if len(matching)==1 else 'postedNeedsDefinitionReconciliation'] += 1
            totals['focusTrials'] += 1
            totals['registeredPrimaryDefinitions'] += len(registered)
            totals['focusTrialsWithPostedPrimary' if posted else 'focusTrialsWithoutPostedPrimary'] += 1
            studies.append({
                'ticker': row.get('ticker'), 'nctId': nct,
                'registryUrl': 'https://clinicaltrials.gov/study/' + nct,
                'originalPacketSha256': digest, 'sourceIntegrityVerified': True,
                'registeredPrimaryCount':len(registered),
                'postedPrimaryCount':len(posted),
                'registeredPrimaryDefinitions':[{
                    'title': r.get('measure'), 'timeFrame': r.get('timeFrame')}
                    for r in registered],
                'postedPrimaryCrosswalk': endpoints,
                'independentScientificReview':'NOT_COMPLETE',
                'approvalProbability':None, 'scientificScore':None,
                'fdaPrediction':'ABSTAIN','productionWriteAllowed':False
            })
    if (totals['focusTrials'] != expected_trials
            or totals['registeredPrimaryDefinitions'] != expected_registered
            or totals['postedPrimaryMeasures'] != expected_posted
            or totals['focusTrialsWithPostedPrimary'] != expected_posted_trials):
        raise ValueError('Source snapshot counts differ from verified dated roster')
    return {
        'schemaVersion':1, 'kind':'FOCUS_PRIMARY_REGISTERED_POSTED_CROSSWALK_UNADJUDICATED',
        'source':'Original ClinicalTrials.gov API-v2 packet cache from recovery run 44120924177',
        'counts':dict(totals), 'scientificReviewsCompleted':0,
        'fdaApprovalProbabilitiesComputed':0,'productionWritesAllowed':False,
        'limits':[
            'Posted primary safety measures are not clinical efficacy endpoints.',
            'A missing posted statistical comparison cannot be interpreted as a trial failure or success.',
            'Matching titles and timeframes do not validate prespecification or the statistical method.',
            'Independent protocol, estimand, missing data, harms and FDA application review remain required.'
        ], 'trials': studies
    }


def markdown(report):
    c=report['counts']
    lines=['# FOCUS registered vs posted primary endpoint crosswalk',
           '', 'Source-only, independent NCT and SHA-256 verified. No scientific scoring.',
           '', f"- Registered primary definitions: **{c['registeredPrimaryDefinitions']}**",
           f"- Posted primary measures: **{c['postedPrimaryMeasures']}**",
           f"- Safety primary measures: **{c['postedSafetyPrimaryMeasures']}**",
           f"- Non-safety primary measures: **{c['postedNonSafetyPrimaryMeasures']}**",
           f"- Posted measures with statistical comparisons: **{c['postedWithStatisticalComparisons']}**",
           f"- Posted measures without statistical comparisons: **{c['postedWithoutStatisticalComparisons']}**",
           f"- Exact registered title/timeframe matches: **{c['postedExactRegisteredMatch']}**",
           '', '| Ticker | NCT | Registered | Posted | Safety primary | Missing statistical comparisons |',
           '|---|---|---:|---:|---:|---:|']
    for t in report['trials']:
        rows=t['postedPrimaryCrosswalk']
        safety=sum(v['sourceMeasureType']=='SAFETY_TOLERABILITY_PRIMARY' for v in rows)
        no_analysis=sum(v['postedStatisticalComparisonCount']==0 for v in rows)
        lines.append(f"| {t['ticker']} | {t['nctId']} | {t['registeredPrimaryCount']} | {t['postedPrimaryCount']} | {safety} | {no_analysis} |")
    lines += ['', 'All 32 NCTs remain scientifically unadjudicated and all FDA predictions abstain.',
              'A posted primary measure is not independently validated clinical evidence.']
    return '\n'.join(lines) + '\n'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--registry-archive',required=True,type=Path)
    p.add_argument('--focus-review-queue',required=True,type=Path)
    p.add_argument('--json-out',required=True,type=Path)
    p.add_argument('--md-out',required=True,type=Path)
    a=p.parse_args()
    report=crosswalk(a.registry_archive,json.loads(a.focus_review_queue.read_text()))
    a.json_out.parent.mkdir(parents=True,exist_ok=True)
    a.json_out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    a.md_out.write_text(markdown(report))
    print(json.dumps(report['counts']))
if __name__=='__main__':
    main()

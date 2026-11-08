#!/usr/bin/env python3
"""Independent exact-NCT inventory and official trial-source ingestion.

Every POOL identity is retained, across all phases and statuses. Metadata screens
are explicitly incomplete scientific assessments. This module neither imports
assessment/score ledgers nor changes the source POOL or FOCUS roster.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import csv
import hashlib
import json
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / 'reports/deep-medical-intelligence'
NCT = re.compile(r'NCT\d{8}')
STATES = ('METADATA_SCREENED_INCOMPLETE', 'FULL_SOURCE_REVIEW', 'SOURCE_UNAVAILABLE')


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def digest(value):
    raw = value if isinstance(value, bytes) else json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()
    return hashlib.sha256(raw).hexdigest()


def read(path, default=None):
    return json.loads(path.read_text()) if path.exists() else default


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
    temp.replace(path)


def source_file(path, root=ROOT):
    raw = path.read_bytes()
    try:
        name = str(path.relative_to(root))
    except ValueError:
        name = str(path)
    return {'path': name, 'sha256': digest(raw), 'bytes': len(raw),
            'filesystemModifiedAt': datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
            'filesystemDateIsNotSourcePublicationDate': True}


def valid_nct(value):
    return isinstance(value, str) and NCT.fullmatch(value) is not None


def registry_identity(nct, document):
    if not valid_nct(nct) or document.get('protocolSection', {}).get('identificationModule', {}).get('nctId') != nct:
        raise ValueError('EXACT_NCT_MISMATCH:' + str(nct))
    # No phase restriction: early-phase, Phase 4 and non-phase records belong here.
    return document


def phase_requirements(phase):
    phases = set(str(phase or 'UNKNOWN').split('|'))
    needed = ['Exact protocol, population, comparator, dates and source provenance',
              'All prespecified endpoints and analysis populations',
              'Adverse events, serious events, withdrawals and follow-up limitations']
    if phases & {'EARLY_PHASE1', 'PHASE1'}:
        needed += ['Dose escalation, dose-limiting toxicity, exposure, pharmacokinetics and pharmacodynamics']
    if phases & {'PHASE2'}:
        needed += ['Dose-response and exploratory clinical signal with uncertainty and multiplicity limitations']
    if phases & {'PHASE3'}:
        needed += ['Prespecified confirmatory effect sizes, confidence intervals, multiplicity and missing-data sensitivity']
    if phases & {'PHASE4'}:
        needed += ['Postmarketing effectiveness, rare harms, comparative exposure and long-term follow-up']
    if phases & {'NA', 'UNKNOWN'} or not phases:
        needed += ['Confirm study type and design-specific applicability; do not impose a Phase 3 efficacy framework']
    return needed


def load_links(path, focus_ids):
    if path is None or not path.exists():
        return [], []
    raw = read(path)
    links = raw.get('links', raw.get('records', [])) if isinstance(raw, dict) else raw
    accepted, rejected = [], []
    for row in links:
        origin = row.get('focusNctId') or row.get('parentNctId') or row.get('nctId')
        linked = row.get('linkedNctId') or row.get('targetNctId')
        source = row.get('sourceUrl') or row.get('evidenceUrl')
        if origin not in focus_ids or not valid_nct(linked) or not isinstance(source, str) or not source.startswith('https://'):
            rejected.append({'record': row, 'reason': 'EXPLICIT_FOCUS_NCT_LINK_AND_SOURCE_REQUIRED'})
            continue
        accepted.append({**row, 'focusNctId': origin, 'linkedNctId': linked, 'sourceUrl': source})
    return accepted, rejected


def build_inventory(pool_path=None, csv_path=None, focus_path=None, links_path=None, root=ROOT):
    pool_path = pool_path or root / 'new-platform/frontend/data/tools-pool-snapshot.json'
    csv_path = csv_path or root / 'data/all_phase_trials.csv'
    focus_path = focus_path or root / 'new-platform/frontend/data/p3PostDataActive.json'
    pool = read(pool_path); focus = read(focus_path)
    rows = list(csv.DictReader(csv_path.open()))
    pipeline = pool['pipeline']; grouped = defaultdict(lambda: {'pool': [], 'csv': [], 'focus': []})
    aliases, regulatory, invalid = [], [], []
    for row in pipeline:
        key = row.get('id', '')
        if key.startswith('TRIAL|'):
            nct = key[6:]
            if not valid_nct(nct):
                invalid.append({'source': 'POOL', 'record': row, 'reason': 'MALFORMED_EXACT_NCT'})
                continue
            grouped[nct]['pool'].append(row)
        elif key.startswith('RESULT|'):
            aliases.append({**row, 'processingState': 'UNLINKED_ALIAS_REQUIRES_EXACT_NCT',
                            'reason': 'Standalone result has no exact NCT; company/drug names cannot establish trial identity.'})
        else:
            regulatory.append(row)
    for row in rows:
        nct = row.get('nct_id')
        if not valid_nct(nct):
            invalid.append({'source': 'ALL_PHASE_CSV', 'record': row, 'reason': 'MALFORMED_EXACT_NCT'})
            continue
        grouped[nct]['csv'].append(row)
    focus_ids = set()
    for row in focus['records']:
        nct = row.get('nct') or row.get('nctId')
        if not valid_nct(nct):
            raise ValueError('MALFORMED_FOCUS_NCT')
        if nct in focus_ids:
            raise ValueError('DUPLICATE_FOCUS_NCT')
        focus_ids.add(nct); grouped[nct]['focus'].append(row)
    links, rejected_links = load_links(links_path, focus_ids)
    for link in links:
        grouped[link['linkedNctId']].setdefault('linked', []).append(link)
    new_phases = {r['nctId']: r.get('officialPhases', []) for r in pool.get('sourceHealth', {}).get('verifiedNewClinicalNcts', [])}
    records, conflicts = [], []
    for nct, sources in sorted(grouped.items()):
        csv_rows = sources['csv']; pool_rows = sources['pool']; focus_rows = sources['focus']
        baseline = csv_rows[0] if csv_rows else {}; published = pool_rows[0] if pool_rows else {}
        def alternatives(field):
            csv_field = {'nctId': 'nct_id'}.get(field, field)
            return sorted({str(r.get(csv_field, '')).strip() for r in csv_rows if str(r.get(csv_field, '')).strip()} |
                          {str(r.get(field, '')).strip() for r in pool_rows if str(r.get(field, '')).strip()})
        discrepancies = {field: values for field in ('ticker', 'company', 'drug', 'indication') if len(values := alternatives(field)) > 1}
        duplicate_sources = {key: len(sources[key]) for key in ('csv', 'pool') if len(sources[key]) > 1}
        if discrepancies or duplicate_sources:
            conflicts.append({'nctId': nct, 'metadataAlternatives': discrepancies, 'duplicateSourceRows': duplicate_sources,
                              'resolution': 'Exact NCT identity retained; source aliases preserved, no company-name trial merge.'})
        record = {'nctId': nct, 'ticker': published.get('ticker') or baseline.get('ticker') or (focus_rows[0].get('ticker') if focus_rows else None),
                  'company': published.get('company') or baseline.get('company'),
                  'drug': published.get('drug') or baseline.get('drug'),
                  'indication': published.get('indication') or baseline.get('indication'),
                  'phase': baseline.get('phase') or '|'.join(new_phases.get(nct, [])) or 'UNKNOWN',
                  'status': baseline.get('status') or 'UNKNOWN_SOURCE_NOT_REPORTED',
                  'poolStage': published.get('stage'), 'membership': {'pool': bool(pool_rows), 'focus': bool(focus_rows), 'linked': bool(sources.get('linked'))},
                  'processingState': 'METADATA_SCREENED_INCOMPLETE',
                  'sourceMetadata': {'allPhaseCsv': csv_rows, 'poolSnapshot': pool_rows, 'focusSnapshot': focus_rows,
                                     'explicitStudyLinks': sources.get('linked', [])},
                  'metadataAlternatives': discrepancies, 'sourceRowDuplicates': duplicate_sources,
                  'scientificReviewComplete': False}
        records.append(record)
    health = pool.get('sourceHealth', {}); parity = health.get('pipelineSourceParity') or health.get('streamlitPipelineParity') or {}
    pool_ncts = {r['nctId'] for r in records if r['membership']['pool']}
    csv_ncts = {r['nct_id'] for r in rows if valid_nct(r.get('nct_id'))}
    counts = {'uniqueInventoryNcts': len(records), 'poolUniqueNcts': len(pool_ncts), 'csvRows': len(rows), 'csvUniqueNcts': len(csv_ncts),
              'focusTrials': len(focus_ids), 'linkedNcts': len({x['linkedNctId'] for x in links}),
              'poolRecords': len(pipeline), 'poolClinicalRecordsIncludingUnlinkedResults': health.get('clinicalRows'),
              'unlinkedResultAliases': len(aliases), 'regulatoryEventsExcludedFromTrialCount': len(regulatory),
              'poolAdditionsBeyondCsv': sorted(pool_ncts - csv_ncts), 'csvNotInPool': sorted(csv_ncts - pool_ncts),
              'duplicateIdentityGroups': sum(bool(r['sourceRowDuplicates']) for r in records),
              'metadataAliasDiscrepancyGroups': len(conflicts), 'statusCounts': dict(Counter(r['status'] for r in records)),
              'phaseCounts': dict(Counter(r['phase'] for r in records))}
    descriptors = [source_file(p, root) for p in (pool_path, csv_path, focus_path)]
    descriptors[0].update({'sourceAsOf': pool.get('asOf'), 'snapshotGeneratedAt': pool.get('snapshotGeneratedAt'), 'sourceState': health.get('state')})
    descriptors[1].update({'sourceCheckedAtMin': min((r.get('checked_at') or '' for r in rows), default=None),
                           'sourceCheckedAtMax': max((r.get('checked_at') or '' for r in rows), default=None)})
    descriptors[2].update({'sourceAsOf': focus.get('asOf'), 'sourceUrl': focus.get('source'),
                           'liveSheetReadbackRequired': True})
    if links_path and links_path.exists():
        descriptors.append(source_file(links_path, root))
    return {'schemaVersion': 1, 'asOf': now(), 'scope': 'ALL_EXACT_POOL_NCTS_PLUS_EXPLICIT_FOCUS_LINKS_ALL_PHASES_ALL_STATUSES',
            'counts': counts, 'sourceFiles': descriptors, 'records': records,
            'scopeFunnelParity': {'sourceImplementation': 'new-platform/frontend/lib/tools-pool-inventory.ts and pool-pipeline-funnel.ts isPoolTrial',
                                 'definition': 'TRIAL|NCT followed by exactly eight digits; RESULT aliases and APPLICATION events are separate.',
                                 'declaredProgramCount': parity.get('exactPrograms'), 'actualProgramRecords': len(pipeline),
                                 'programCountMatches': parity.get('exactPrograms') == len(pipeline),
                                 'clinicalRowCountMatches': health.get('clinicalRows') == len(pool_ncts) + len(aliases),
                                 'sourceState': health.get('state'), 'fullScientificReviewImplied': False},
            'unlinkedAliases': aliases, 'regulatoryEventsExcluded': regulatory, 'conflicts': conflicts,
            'invalidSourceRows': invalid, 'rejectedStudyLinks': rejected_links,
            'limitations': ['All rows have a metadata screen, not a complete clinical/scientific analysis.',
                           'Source aliases are preserved and require exact trial/program review; no company-name link is inferred.',
                           'Terminated, withdrawn, suspended, completed and unknown statuses are retained.',
                           'FOCUS membership is read from its existing snapshot; live Google Sheets parity is a separate verification.']}


class RegistryClient:
    def __init__(self, report=REPORT, timeout=35, retries=3):
        self.report = report; self.cache = report / 'registry-cache'; self.cache.mkdir(parents=True, exist_ok=True)
        self.state = read(report / 'ingestion-state.json', {'schemaVersion': 1, 'sources': {}, 'attempts': []})
        self.timeout = timeout; self.retries = retries

    def save(self):
        write(self.report / 'ingestion-state.json', self.state)

    def cached(self, nct):
        source = self.state['sources'].get(nct)
        if not source or not source.get('versions'):
            return None, None
        version = source['versions'][-1]; path = self.report / version['cachePath']
        if not path.exists():
            return None, source
        document = registry_identity(nct, read(path))
        if digest(document) != version['fingerprint']:
            raise ValueError('REGISTRY_CACHE_FINGERPRINT_MISMATCH:' + nct)
        return document, source

    def accept(self, nct, document, origin, retrieved_at=None):
        registry_identity(nct, document); fingerprint = digest(document)
        path = self.cache / (nct + '-' + fingerprint + '.json')
        if not path.exists(): write(path, document)
        source = self.state['sources'].setdefault(nct, {'nctId': nct, 'url': 'https://clinicaltrials.gov/api/v2/studies/' + nct, 'versions': []})
        previous = source['versions'][-1] if source['versions'] else None
        if not previous or previous['fingerprint'] != fingerprint:
            source['versions'].append({'fingerprint': fingerprint, 'previousFingerprint': previous['fingerprint'] if previous else None,
                                       'cachePath': str(path.relative_to(self.report)), 'retrievedAt': retrieved_at,
                                       'capturedAt': now(), 'origin': origin})
        if origin == 'OFFICIAL_CT_GOV_API_V2': source['lastSuccessfulRemoteRetrievalAt'] = retrieved_at
        return source

    def fetch(self, nct, resume=False):
        old_doc, source = self.cached(nct)
        if resume and source and str(source.get('lastSuccessfulRemoteRetrievalAt', '')).startswith(now()[:10]):
            return nct, old_doc, None, 'RESUMED_CURRENT_DAY_REMOTE_CAPTURE'
        url = 'https://clinicaltrials.gov/api/v2/studies/' + nct
        error = None
        for attempt in range(self.retries):
            try:
                with urlopen(Request(url, headers={'User-Agent': 'PDUFA exact-NCT public-source clinical research'}), timeout=self.timeout) as response:
                    document = json.load(response)
                registry_identity(nct, document)
                return nct, document, None, 'OFFICIAL_CT_GOV_API_V2'
            except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
                error = type(exc).__name__ + ': ' + str(exc)[:300]
                if attempt + 1 < self.retries: time.sleep(min(8, 2 ** attempt))
        return nct, old_doc, error, 'REMOTE_SOURCE_UNAVAILABLE_PRIOR_CACHE_PRESERVED' if old_doc else 'SOURCE_UNAVAILABLE'


def import_official_caches(client, ncts, root=ROOT):
    imported = 0
    # Only raw protocolSection/resultsSection API-shaped files are read. No
    # assessment, evidence, survey, score, or prediction ledger is imported.
    for path in sorted((root / 'reports').glob('*/sources/*-registry.json')):
        nct = path.name.split('-')[0]
        if nct not in ncts or nct in client.state['sources']:
            continue
        try:
            document = registry_identity(nct, read(path))
        except (ValueError, TypeError, KeyError):
            continue
        source = client.accept(nct, document, 'REUSED_RAW_OFFICIAL_REGISTRY_CACHE')
        source['reusedRawFile'] = source_file(path, root)
        imported += 1
    client.save()
    return imported


def trial_analysis(record, document=None, source=None, error=None):
    nct = record['nctId']; phase = record['phase']; status = record['status']
    if document:
        registry_identity(nct, document)
        protocol = document['protocolSection']; phases = protocol.get('designModule', {}).get('phases', [])
        phase = '|'.join(phases) if phases else 'NA'
        status = protocol.get('statusModule', {}).get('overallStatus', status)
    else:
        protocol = None
    endpoints = (document or {}).get('resultsSection', {}).get('outcomeMeasuresModule', {}).get('outcomeMeasures', [])
    state = 'SOURCE_UNAVAILABLE' if error and not document else 'METADATA_SCREENED_INCOMPLETE'
    return {'schemaVersion': 1, 'nctId': nct, 'ticker': record.get('ticker'), 'company': record.get('company'),
            'drug': record.get('drug'), 'indication': record.get('indication'), 'phase': phase, 'status': status,
            'membership': record['membership'], 'processingState': state, 'scientificReviewComplete': False,
            'assessmentAsOf': now(), 'phaseAppropriateEvidenceRequirements': phase_requirements(phase),
            'metadataAssessment': {'exactRegistryIdentityChecked': bool(document), 'officialSourceCaptured': bool(document),
                                   'registryResultsAvailable': bool((document or {}).get('resultsSection')),
                                   'allEndpointsRetained': True, 'endpointCount': len(endpoints),
                                   'interpretation': 'Registry metadata/results capture is not complete scientific review or evidence of success.'},
            'registeredDesign': protocol.get('designModule') if protocol else None,
            'registeredOutcomes': protocol.get('outcomesModule') if protocol else None,
            'registeredArms': protocol.get('armsInterventionsModule') if protocol else None,
            'rawResults': (document or {}).get('resultsSection'), 'endpoints': endpoints,
            'registryDocument': document, 'sourceProvenance': source,
            'lastSourceError': error,
            'missingEvidence': ['Independent original-source interpretation and relevant publications, statistical plans, clinical significance, safety context and limitations remain to be reviewed.'] + ([] if document else ['Complete official registry packet not yet captured by this independent collector.'])}


def run(args, root=ROOT, report=None):
    report = report or root / 'reports/deep-medical-intelligence'
    inventory = build_inventory(links_path=args.links, root=root)
    client = RegistryClient(report, retries=args.retries, timeout=args.timeout)
    ncts = {r['nctId'] for r in inventory['records']}
    imported = import_official_caches(client, ncts, root)
    selected = set(args.nct)
    if args.fetch_focus:
        selected |= {r['nctId'] for r in inventory['records'] if r['membership']['focus'] or r['membership']['linked']}
    if args.fetch_all:
        selected |= ncts
    if selected - ncts:
        raise ValueError('NCT_NOT_IN_EXACT_INVENTORY:' + ','.join(sorted(selected - ncts)))
    job_path = report / 'ingestion-job.json'
    job = read(job_path, {'schemaVersion': 1, 'attemptedNcts': [], 'events': []})
    if selected:
        job.update({'startedAt': now(), 'selectedNcts': sorted(selected), 'state': 'RUNNING', 'workers': args.workers})
        write(job_path, job)
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(client.fetch, nct, args.resume): nct for nct in sorted(selected)}
            for future in as_completed(futures):
                nct, doc, error, origin = future.result(); stamp = now()
                if doc and origin == 'OFFICIAL_CT_GOV_API_V2': client.accept(nct, doc, origin, stamp)
                event = {'nctId': nct, 'url': 'https://clinicaltrials.gov/api/v2/studies/' + nct, 'at': stamp, 'state': origin, 'error': error}
                client.state['attempts'].append(event)
                if error: client.state['sources'].setdefault(nct, {'nctId': nct, 'url': event['url'], 'versions': []})['lastError'] = error
                else: client.state['sources'][nct].pop('lastError', None)
                client.save()
                if nct not in job['attemptedNcts']: job['attemptedNcts'].append(nct)
                job['events'].append(event); write(job_path, job)
        job.update({'finishedAt': now(), 'state': 'COMPLETED_WITH_SOURCE_ERRORS' if any(e['error'] for e in job['events'] if e['nctId'] in selected) else 'COMPLETED'})
        write(job_path, job)
    analyses = []
    for record in inventory['records']:
        doc, source = client.cached(record['nctId'])
        error = source.get('lastError') if source else None
        analysis = trial_analysis(record, doc, source, error)
        record.update({'processingState': analysis['processingState'], 'phase': analysis['phase'], 'status': analysis['status'],
                       'rawRegistryCaptured': bool(doc), 'sourceRefreshError': error,
                       'ingestionState': 'CAPTURED' if doc else 'SOURCE_UNAVAILABLE' if error else 'QUEUED_NOT_YET_FETCHED'})
        analyses.append(analysis)
    inventory['counts'].update({'processingStates': dict(Counter(r['processingState'] for r in inventory['records'])),
                                'rawRegistryPacketsCaptured': sum(r['rawRegistryCaptured'] for r in inventory['records']),
                                'fullySourceReviewed': 0, 'scientificReviewIncomplete': len(inventory['records']),
                                'sourceUnavailable': sum(r['processingState'] == 'SOURCE_UNAVAILABLE' for r in inventory['records']),
                                'statusCounts': dict(Counter(r['status'] for r in inventory['records'])),
                                'phaseCounts': dict(Counter(r['phase'] for r in inventory['records']))})
    inventory['ingestion'] = {'importedRawRegistryCaches': imported, 'freshFetchSelected': len(selected),
                              'persistentJobPath': str(job_path.relative_to(root)),
                              'remainingFetchQueue': sum(r['ingestionState'] == 'QUEUED_NOT_YET_FETCHED' for r in inventory['records']),
                              'resumePolicy': 'Reuse current-UTC-day successful remote captures; older caches are refreshed when selected.',
                              'remainingPoolCommand': 'python scripts/collect_deep_medical_intelligence.py --all --fetch-all --resume',
                              'arbitraryTrialCountCap': None}
    write(report / 'inventory.json', inventory)
    temp = report / 'trial-analysis.jsonl.tmp'
    with temp.open('w') as out:
        for analysis in analyses: out.write(json.dumps(analysis, ensure_ascii=False, separators=(',', ':')) + '\n')
    temp.replace(report / 'trial-analysis.jsonl')
    summary = {'asOf': now(), 'counts': inventory['counts'], 'ingestion': inventory['ingestion'],
               'inputSourceHashes': {s['path']: s['sha256'] for s in inventory['sourceFiles']}}
    write(report / 'ingestion-summary.json', summary)
    print(json.dumps(summary, ensure_ascii=False))
    return summary


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--all', action='store_true', help='Process every inventory identity, including metadata-only records.')
    p.add_argument('--resume', action='store_true')
    p.add_argument('--fetch-focus', action='store_true', help='Fresh official source fetch for current FOCUS and explicitly linked NCTs.')
    p.add_argument('--fetch-all', action='store_true', help='Persistent resumable official-source ingestion for the entire POOL, without a trial-count cap.')
    p.add_argument('--nct', action='append', default=[])
    p.add_argument('--report', action='store_true')
    p.add_argument('--links', type=Path)
    p.add_argument('--workers', type=int, default=4)
    p.add_argument('--retries', type=int, default=3)
    p.add_argument('--timeout', type=int, default=35)
    args = p.parse_args(argv)
    if not (args.all or args.report or args.nct or args.fetch_focus or args.fetch_all): p.error('Choose --all, --nct, --fetch-focus, --fetch-all or --report')
    if min(args.workers, args.retries, args.timeout) < 1: p.error('workers/retries/timeout must be positive')
    run(args)

if __name__ == '__main__':
    main()

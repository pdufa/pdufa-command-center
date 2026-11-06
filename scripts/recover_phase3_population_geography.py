"""Resumable exact-NCT ClinicalTrials.gov population/site documentary recovery.

Does not adjudicate eligibility adequacy, representativeness or clinical outcomes.
Successful batches persist atomically; failed refreshes retain dated prior records.
"""
import argparse
import concurrent.futures
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import time
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'new-platform/frontend/data/phase3PopulationGeography20261106.json'
ROSTER = ROOT / 'new-platform/frontend/public/phase3-unified-classifications-2026-11-05.json'

def project(study, requested, retrieved, sha):
    p = study.get('protocolSection', {})
    ident = p.get('identificationModule', {})
    nct = ident.get('nctId')
    if nct not in requested or not re.fullmatch(r'NCT\d{8}', nct or ''):
        raise ValueError('UNREQUESTED_NCT_IDENTITY')
    eligibility = p.get('eligibilityModule', {})
    locations = p.get('contactsLocationsModule', {}).get('locations', [])
    updated = p.get('statusModule', {}).get('lastUpdatePostDateStruct', {}).get('date')
    # Date of source publication must be present; retrieval time is separate.
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', updated or ''):
        raise ValueError('REGISTRY_PUBLICATION_DATE_UNAVAILABLE')
    dt.date.fromisoformat(updated)
    if updated > retrieved[:10]:
        raise ValueError('FUTURE_REGISTRY_PUBLICATION_DATE')
    return dict(nctId=nct, sourceState='FETCHED', sourceUrl='https://clinicaltrials.gov/study/'+nct,
        publicationDate=updated, retrievedAt=retrieved, batchSha256=sha,
        sponsorProtocol=ident.get('orgStudyIdInfo', {}).get('id', ''), acronym=ident.get('acronym', ''),
        title=ident.get('briefTitle', ''), registeredSponsor=p.get('sponsorCollaboratorsModule', {}).get('leadSponsor', {}).get('name', ''),
        conditions=p.get('conditionsModule', {}).get('conditions', []),
        minimumAge=eligibility.get('minimumAge', ''), maximumAge=eligibility.get('maximumAge', ''),
        sex=eligibility.get('sex', ''), healthyVolunteers=eligibility.get('healthyVolunteers'),
        eligibilityCriteria=eligibility.get('eligibilityCriteria', ''),
        registeredLocationCount=len(locations),
        countries=sorted({x['country'] for x in locations if x.get('country')}),
        criticalReviewStatus='NOT_YET_REVIEWED', scope='REGISTERED_DESIGN_NOT_OBSERVED_BASELINE_OR_PREDICTION')

def collect(ids):
    url = 'https://clinicaltrials.gov/api/v2/studies?' + urllib.parse.urlencode({
        'filter.ids': ','.join(ids), 'pageSize': 100, 'format': 'json'})
    error = None
    for attempt in range(2):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'Accept':'application/json'}), timeout=35) as response:
                body = response.read(12_000_000)
            payload = json.loads(body)
            if payload.get('nextPageToken'):
                raise ValueError('UNEXPECTED_PAGINATION')
            sha = hashlib.sha256(body).hexdigest()
            now = dt.datetime.now(dt.timezone.utc).isoformat()
            records = [project(s, set(ids), now, sha) for s in payload['studies']]
            for record in records:
                record['batchApiUrl'] = url
            if len({r['nctId'] for r in records}) != len(records):
                raise ValueError('DUPLICATE_REGISTRY_IDENTITIES')
            returned = {r['nctId'] for r in records}
            return records, [dict(nctId=n, blocker='NOT_RETURNED_IN_BATCH', sourceUrl=url) for n in ids if n not in returned]
        except Exception as exc:
            error = str(exc)
            if attempt == 0:
                time.sleep(1)
    return [], [dict(nctId=n, blocker=error, sourceUrl=url) for n in ids]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--refresh', action='store_true', help='Refresh successful saved records too')
    args = parser.parse_args()
    roster = json.loads(ROSTER.read_text())['rows']
    ids = [r['nctId'] for r in roster]
    if len(ids) != 762 or len(set(ids)) != 762:
        raise ValueError('CENSUS_IDENTITY_MISMATCH')
    existing = json.loads(DATA.read_text()) if DATA.exists() else {'records':[], 'attempts':[]}
    records = {r['nctId']:r for r in existing['records'] if r['nctId'] in ids}
    pending = [n for n in ids if args.refresh or n not in records]
    attempts = []
    def save():
        snapshot = dict(schemaVersion=1, scope='Exact-NCT registered eligibility and geographic source facts; no scientific scores.',
            asOf=dt.datetime.now(dt.timezone.utc).isoformat(), censusTrials=len(ids),
            records=[records[n] for n in ids if n in records], attempts=attempts,
            missingNcts=[n for n in ids if n not in records])
        temp = DATA.with_suffix('.tmp')
        temp.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False)+'\n')
        temp.replace(DATA)
    chunks = [pending[i:i+25] for i in range(0, len(pending), 25)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for future in concurrent.futures.as_completed([pool.submit(collect, chunk) for chunk in chunks]):
            fetched, blockers = future.result()
            records.update({r['nctId']:r for r in fetched})
            attempts.extend(blockers)
            save()
            print(f'{len(records)}/762 registry records recovered; {len(attempts)} refresh blockers', flush=True)
    save()

if __name__ == '__main__':
    main()

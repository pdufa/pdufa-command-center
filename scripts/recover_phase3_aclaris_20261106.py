"""Idempotent reviewed Aclaris recovery. Source snapshots are exact-NCT registry data.

Run with the downloaded registry JSON directory (default /tmp/aclaris-recovery).
No retrospective forecasts, inferred efficacy verdicts or pooled trial assignments.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'new-platform/frontend/data'
IDS = {
    'NCT02667236': 'A-101-SEBK-301', 'NCT02667275': 'A-101-SEBK-302',
    'NCT02667288': 'A-101-SEBK-303', 'NCT03687372': 'A-101-WART-301',
    'NCT03691831': 'A-101-WART-302', 'NCT03812510': 'A-101-WART-303',
}
SEBK = 'https://investor.aclaristx.com/static-files/01e1e9f5-563a-412b-bc6c-a51de0a8837c'
WART1 = 'https://investor.aclaristx.com/news-releases/news-release-details/aclaris-therapeutics-101-45-topical-solution-meets-primary-and-1'
WART2 = WART1[:-1] + '0'
FDA = 'https://www.accessdata.fda.gov/drugsatfda_docs/nda/2017/209305Orig1s000MedR.pdf'
STATS = 'https://www.accessdata.fda.gov/drugsatfda_docs/nda/2017/209305Orig1s000StatR.pdf'
APPROVAL = 'https://www.accessdata.fda.gov/drugsatfda_docs/appletter/2017/209305Orig1s000ltr.pdf'


def main(source_dir):
    read = lambda name: json.loads((ROOT / name).read_text())
    def write(name, value):
        (ROOT / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
    ir = read('phase3CompanyWebsiteEvidence20261105.json')
    endpoints = read('phase3EndpointAdjudications20261105.json')
    queue = read('phase3InvestorRelationsResearchQueue20261106.json')
    records, facts, raw = [], [], []

    def fact(nct, q, evidence, url, date, status='DOCUMENTED_SOURCE_FACT', **extra):
        facts.append(dict(nctId=nct, assessmentNumber=q, classification=status,
                          evidence=evidence, sourceUrl=url, publicationDate=date,
                          reviewedAt='2026-11-06', sourceLocator=extra.pop('sourceLocator', 'Exact trial registry results'),
                          evidenceScope='HISTORICAL_SOURCE_FACT_NOT_PREDICTION', **extra))

    summaries = {
        'NCT02667236': ('PRIMARY_ENDPOINT_MET', SEBK, '2016-11-15',
                        'SEBK-301: complete clearance of four lesions at day 106: 9/223 active versus 0/227 vehicle; issuer p<0.002. FDA statistical review independently supports success.'),
        'NCT02667275': ('PRIMARY_ENDPOINT_MET', SEBK, '2016-11-15',
                        'SEBK-302: complete clearance of four lesions at day 106: 19/244 active versus 0/243 vehicle; issuer p<0.0001.'),
        'NCT02667288': ('NO_BINARY_PASS_FAIL', FDA, '2017-11-21',
                        'SEBK-303 is a separate open-label single-group study, not a pivotal-trial extension. Registry primary clearance at day 148: 16/147; no randomized efficacy comparison or binary success threshold.'),
        'NCT03687372': ('PRIMARY_ENDPOINT_MET', WART1, '2019-10-24',
                        'THWART-1 (WART-301): all baseline warts clear at day 60 in 40/254 active versus 13/249 vehicle; p=0.0003.'),
        'NCT03691831': ('PRIMARY_ENDPOINT_MET', WART2, '2019-09-16',
                        'THWART-2 (WART-302): all baseline warts clear at day 60 in 33/251 active versus 8/251 vehicle; issuer p<0.0001. Registry displays p=0.0001 without a modifier; original-source precision retained.'),
        'NCT03812510': ('NO_BINARY_PASS_FAIL', 'https://clinicaltrials.gov/study/NCT03812510', '2020-11-23',
                        'WART-303 is an open-label safety extension with no efficacy pass/fail threshold. TEAEs: 70/163 previously-active and 116/213 previously-vehicle participants; all received active extension treatment. These are prior-treatment strata, not concurrent active/control arms.'),
    }
    endpoints['records'] = [r for r in endpoints['records'] if r['nctId'] not in IDS]
    for nct, protocol in IDS.items():
        payload = (source_dir / (nct + '.json')).read_bytes()
        r = json.loads(payload)
        p = r['protocolSection']; results = r['resultsSection']
        identity = p['identificationModule']
        assert identity['nctId'] == nct and identity['orgStudyIdInfo']['id'] == protocol
        url = 'https://clinicaltrials.gov/study/' + nct
        date = p['statusModule']['lastUpdatePostDateStruct']['date']
        assert date <= '2026-11-06'
        raw.append(dict(nctId=nct, sponsorProtocol=protocol, sourceUrl=url,
                        publicationDate=date, retrievedAt='2026-11-06',
                        sourceSha256=hashlib.sha256(payload).hexdigest(), registry=r))
        outcome, primary_url, primary_date, summary = summaries[nct]
        crosswalk = f'Exact registry {nct} = {protocol}; hydrogen peroxide; ' + '; '.join(p['conditionsModule']['conditions'])
        endpoints['records'].append(dict(nctId=nct, endpointOutcome=outcome, rationale=summary,
            evidenceUrl=primary_url, sourceDate=primary_date, reviewedAt='2026-11-06',
            evidenceType='EXACT_PROTOCOL_ISSUER_FDA_REGISTRY_CROSSWALK', identityCrosswalk=crosswalk,
            identityEvidenceUrl=url, qualification='Historical observation only. Open-label descriptive outcomes are not efficacy successes.'))
        fact(nct, 1, summary, primary_url, primary_date,
             'DOCUMENTED_NON_BINARY_ENDPOINT' if outcome == 'NO_BINARY_PASS_FAIL' else 'DOCUMENTED_PRIMARY_ENDPOINT_MET')
        design = p['designModule']; info = design['designInfo']
        primary = p['outcomesModule']['primaryOutcomes'][0]
        for q, text in {
            7: primary['measure'], 8: primary['timeFrame'],
            9: 'Registered allocation: ' + info['allocation'] + '; model: ' + info['interventionModel'],
            10: 'Registered masking: ' + info['maskingInfo']['masking'] + '. No independent assessment of masking integrity.',
            11: ('Single-group open-label active treatment; no concurrent comparator.' if info['interventionModel'] == 'SINGLE_GROUP'
                 else 'Randomized hydrogen peroxide versus topical vehicle. Vehicle control is not an active standard-of-care comparison.'),
            12: f"Registry enrollment {design['enrollmentInfo']['count']} ({design['enrollmentInfo']['type']}); safety denominators may differ.",
            25: 'Registry operational status: ' + p['statusModule']['overallStatus'],
            29: 'Trial-specific results are publicly posted; historical observation, not an unreleased forecast.',
        }.items():
            fact(nct, q, text, url, date)
        ae = results['adverseEventsModule']; groups = ae['eventGroups']
        serious = '; '.join(f"{g['title']}: {g['seriousNumAffected']}/{g['seriousNumAtRisk']} participants with all-cause SAEs; deaths {g['deathsNumAffected']}/{g['deathsNumAtRisk']}" for g in groups)
        common = '; '.join(f"{g['title']}: {g['otherNumAffected']}/{g['otherNumAtRisk']} with reported non-serious events" for g in groups)
        fact(nct, 3, common + f". Reporting threshold {ae['frequencyThreshold']}%; not a safety acceptability score or treatment-related rate.", url, date)
        fact(nct, 23, serious + '. Participant counts, not event counts; no inference of causality or zero unobserved risk.', url, date)
        infections = [e for e in ae.get('otherEvents', []) if 'infection' in e.get('organSystem', '').lower()]
        names = {g['id']: g['title'] for g in groups}
        infection_text = '; '.join(e['term'] + ': ' + ', '.join(f"{names[s['groupId']]} {s['numAffected']}/{s['numAtRisk']}" for s in e['stats']) for e in infections)
        if infection_text:
            fact(nct, 22, infection_text + f". Registry non-serious infection categories at {ae['frequencyThreshold']}% reporting threshold; participants may occur in multiple categories. No causal or manageability conclusion.", url, date)
        flow = results['participantFlowModule']; labels = {g['id']: g['title'] for g in flow['groups']}
        flow_text = '; '.join(m['type'] + ': ' + ', '.join(labels[x['groupId']] + ' ' + x['numSubjects'] for x in m['achievements']) for m in flow['periods'][0]['milestones'])
        withdrawal_text = '; '.join(d['type'] + ': ' + ', '.join(labels[x['groupId']] + ' ' + x['numSubjects'] for x in d['reasons']) for d in flow['periods'][0].get('dropWithdraws', []))
        fact(nct, 24, flow_text + '. Noncompletion reasons: ' + withdrawal_text + '. Registry completion classifications can differ from FDA disposition analysis; no inference of treatment-related withdrawal.', url, date)
        company_url = SEBK if 'SEBK' in protocol else WART1 if nct == 'NCT03687372' else WART2 if nct == 'NCT03691831' else 'https://investor.aclaristx.com/node/9706'
        records.append(dict(nctId=nct, ticker='ACRS', company='Aclaris Therapeutics', study=protocol,
                            drug='hydrogen peroxide 40%' if 'SEBK' in protocol else 'hydrogen peroxide 45%',
                            sourceDate=primary_date, companyUrl=company_url,
                            endpointInterpretation='NON_BINARY' if outcome == 'NO_BINARY_PASS_FAIL' else 'PRIMARY_MET',
                            specificEvidence=summary, safetyEvidence=serious, crosswalk=crosswalk))

    for nct, secondary in [('NCT02667236', '13.5% versus 0%'), ('NCT02667275', '23.0% versus 0%')]:
        fact(nct, 17, f'At least three of four lesions cleared at day 106: {secondary}; p<0.0001. Individual-trial secondary result.', SEBK, '2016-11-15')
        fact(nct, 14, 'Missing day-106 lesion scores treated as nonresponders; per-protocol and 50-dataset monotone-logistic multiple-imputation sensitivity analyses. FDA found similar conclusions; this is reviewer documentation, not a numerical robustness grade.', STATS, '2017-10-20', sourceLocator='Section 3.2.1 and sensitivity analyses')
        fact(nct, 28, 'NDA 209305 FDA review evaluates this exact sponsor protocol as a pivotal efficacy study. Original review: standard; historical PDUFA goal December 24, 2017. Goal date is not approval date or a future catalyst.', FDA, '2017-11-21', sourceLocator='Cover and sections 5–6')
    for nct in ['NCT02667236', 'NCT02667275', 'NCT02667288']:
        record = next(x for x in records if x['nctId'] == nct)
        record.update(regulatoryProgramId='NDA_209305_ESKATA_RAISED_SEBORRHEIC_KERATOSES',
                      regulatoryEvidenceStatus='FDA_APPROVED_HISTORICAL', regulatoryReviewType='STANDARD',
                      regulatoryEvidence='NDA 209305 original approval December 14, 2017 for raised seborrheic keratoses; FDA review explicitly identifies this protocol. Historical linkage does not imply current commercialization or extend to 45% wart treatment.',
                      regulatoryEvidenceUrl=APPROVAL, regulatorySourceDate='2017-12-14',
                      regulatoryIdentityEvidenceUrl=FDA)
        fact(nct, 30, record['regulatoryEvidence'], APPROVAL, '2017-12-14',
             sourceLocator='Approval letter; protocol identity in companion FDA medical review', identityEvidenceUrl=FDA)

    for nct, secondary, durability in [
        ('NCT03687372', 'Mean wart clearance at day 137: 28.6% active versus 14.5% vehicle, p<0.0001.', 'Complete clearance at day 137: 22.4% versus 11.6%, p=0.0024.'),
        ('NCT03691831', 'Mean wart clearance at day 137: 27.7% active versus 12.2% vehicle, p<0.0001.', 'Complete clearance at day 137: 22.3% versus 10.0%, p=0.0001.'),
    ]:
        fact(nct, 17, secondary, WART1, '2019-10-24', sourceLocator='Separate THWART-1 and THWART-2 table columns')
        fact(nct, 21, durability + ' Twelve weeks after last treatment; no extrapolation beyond follow-up.', WART1, '2019-10-24')
        raw_record = next(x['registry'] for x in raw if x['nctId'] == nct)
        doc = next(d for d in raw_record['documentSection']['largeDocumentModule']['largeDocs'] if d['typeAbbrev'] == 'Prot')
        docurl = f"https://cdn.clinicaltrials.gov/large-docs/{nct[-2:]}/{nct}/{doc['filename']}"
        for q, text in {
            13: 'Planned about 500 subjects; per-wart response assumption 26% active versus 9% vehicle, modeled at least 11-point patient-response difference, >90% power; additional simulation estimated 97% power.',
            14: 'Missing endpoint wart scores treated as not clear; PP, FCS multiple imputation, tipping-point and site-stratified sensitivity analyses specified. No robustness score assigned.',
            15: 'Four secondary endpoints tested in fixed sequence at two-sided alpha .05, with later confirmatory claims conditional on prior significance. No independent adequacy grade assigned.',
        }.items():
            fact(nct, q, text, docurl, doc['uploadDate'][:10], sourceLocator='Protocol sections 15.1–15.3',
                 sourceDocumentDate=doc['date'], publicUploadDate=doc['uploadDate'][:10],
                 chronologyQualification='This public version was uploaded after readout; not prospective prediction input or proof of preregistration.')
    nct = 'NCT03812510'
    docurl = 'https://cdn.clinicaltrials.gov/large-docs/10/NCT03812510/SAP_002.pdf'
    for q, text in {
        13: 'Exposure-based sample planning: about 400 recruits to obtain >100 subjects with repeat active treatment. No powered superiority comparison in this single-arm extension.',
        14: 'SAP uses safety population for both safety and efficacy, changing the protocol ITT plan. Missing PWA treated as not clear; observed-data sensitivity specified.',
        15: 'SAP states efficacy analyses are descriptive with no formal between-group statistical test. Prior-treatment strata must not be treated as randomized extension arms.',
    }.items():
        fact(nct, q, text, docurl, '2020-09-23', sourceLocator='SAP sections 3.10, 3.13–3.14',
             sourceDocumentDate='2020-01-17', publicUploadDate='2020-09-23',
             chronologyQualification='Publicly uploaded after study completion; historical documentation only.')
    # Keep conflicts visible instead of silently reconciling dissimilar denominators.
    fact('NCT02667275', 20, 'Registry reports 233/244 and 228/243 completed; FDA disposition table reports 0 and 8 discontinued. Protocol-deviation exclusions and differing definitions require reconciliation. No clinical-importance score inferred.', FDA, '2017-11-21', 'REQUIRES_INTERPRETATION', sourceLocator='Table 18 versus registry participant flow')
    fact('NCT03812510', 20, 'Registry flow starts 426, whereas safety analysis includes 376. Published registry group labels refer to prior randomization; denominator and treatment-cycle differences require interpretation.', 'https://clinicaltrials.gov/study/NCT03812510', '2020-11-23', 'REQUIRES_INTERPRETATION')

    ir['records'] = [r for r in ir['records'] if r['nctId'] not in IDS] + records
    ir['assessmentRecords'] = [r for r in ir['assessmentRecords'] if r['nctId'] not in IDS] + facts
    ir['trialCount'] = len(ir['records']); ir['companyCount'] = len({r['ticker'] for r in ir['records']})
    ir['regulatoryApplicationLinkCount'] = sum(bool(r.get('regulatoryEvidenceStatus')) for r in ir['records'])
    ir['regulatoryApplicationProgramCount'] = len({r['regulatoryProgramId'] for r in ir['records'] if r.get('regulatoryProgramId')})
    endpoints['totalReviewed'] = len(endpoints['records'])
    endpoints['counts'] = {k: sum(r['endpointOutcome'] == k for r in endpoints['records']) for k in endpoints['counts']}
    company = next(c for c in queue['companies'] if c['ticker'] == 'ACRS')
    company.update(officialInvestorRelationsUrl='https://investor.aclaristx.com/', searchStatus='PARTIALLY_REVIEWED')
    for trial in company['trials']:
        trial.update(identityMatched=True, assessmentReviewStatus='PARTIALLY_REVIEWED', questionReview=[
            dict(number=q, status=next((f['classification'] for f in facts if f['nctId'] == trial['nctId'] and f['assessmentNumber'] == q), 'NOT_YET_REVIEWED')) for q in range(1,31)])
    company['blockers'] = [
        'USER_DIRECTION_REQUESTED: Q18 patient-reported outcome instruments/results and Q20 clinical-importance thresholds not located in reviewed manufacturer IR/science pages, registry results, protocols or FDA reviews. Not classified as NOT_PUBLICLY_DISCLOSED.',
        'USER_DIRECTION_REQUESTED: WART-301/302/303 exact 45% wart NDA acceptance/FDA correspondence and any target date not located in reviewed manufacturer disclosures. Eskata 40% approval cannot be borrowed.',
        'REQUIRES_INTERPRETATION: SEBK-302 completion versus FDA discontinuation definitions; WART-303 enrolled versus safety denominators. Source values preserved.',
        'ACCESS_BLOCKER: manufacturer THWART PDF downloads returned HTTP 503 through shell; original manufacturer HTML was read through web reader instead.',
    ]
    write('phase3CompanyWebsiteEvidence20261105.json', ir)
    write('phase3EndpointAdjudications20261105.json', endpoints)
    write('phase3InvestorRelationsResearchQueue20261106.json', queue)
    write('phase3AclarisRegistrySources20261106.json', dict(asOf='2026-11-06', scope='Exact-NCT historical evidence, no predictions', records=raw))
    print(json.dumps(dict(newAssessmentRecords=len(facts), classifications={s: sum(f['classification']==s for f in facts) for s in sorted({f['classification'] for f in facts})}, endpoints=endpoints['counts'])))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-dir', type=Path, default=Path('/tmp/aclaris-recovery'))
    main(parser.parse_args().source_dir)

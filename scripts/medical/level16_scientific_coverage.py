#!/usr/bin/env python3
"""Read-only clinical research coverage; collection never confers authentication.

Uses saved receipts, not network calls, reviewer credentials or prediction history.
PubMed linkage is an indexing observation, not proof that a paper reports this trial.
"""
from __future__ import annotations

import copy
from datetime import date, datetime, timezone
import hashlib
import importlib.util
import re
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]


def preparation():
    spec = importlib.util.spec_from_file_location('level16_preparation', Path(__file__).with_name('level16_research_preparation.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_receipt(receipt, cutoff, original):
    """Verify retained bytes and receipt dates, explicitly NOT provenance."""
    timestamp = datetime.fromisoformat(receipt['retrievedAt'].replace('Z', '+00:00'))
    if (timestamp.tzinfo is None or timestamp.astimezone(timezone.utc).date() > date.fromisoformat(cutoff)
            or receipt.get('evidenceCutoffDate') != cutoff
            or receipt.get('provenanceIndependentlyAuthenticated') is not False
            or receipt.get('independentlyScientificallyReviewed') is not False
            or receipt.get('state') != 'HASH_CHECKED'
            or hashlib.sha256(original).hexdigest() != receipt.get('documentSha256')
            or len(original) != receipt.get('byteCount')):
        raise ValueError('Invalid bytes, cutoff or unsupported authentication claim')
    return {key: value for key, value in receipt.items() if key != 'localPath'}


def publication_records(xml_bytes, receipt, cutoff):
    """Metadata only: never store abstracts/full copyrighted articles in Git.

    Require a complete publication date by cutoff; imprecise/future dates remain
    visible discovery leads but cannot count as collected in-cutoff research.
    """
    clean = verify_receipt(receipt, cutoff, xml_bytes)
    if b'<!DOCTYPE' in xml_bytes.upper() or b'<!ENTITY' in xml_bytes.upper():
        # PubMed's standard external DTD is declarative; no entity loading occurs.
        if b'<!ENTITY' in xml_bytes.upper():
            raise ValueError('Entity-bearing evidence rejected')
    root = ET.fromstring(xml_bytes)
    records = {}
    for article in root.findall('./PubmedArticle'):
        pmid = article.findtext('./MedlineCitation/PMID')
        if not pmid or not pmid.isdigit() or pmid in records:
            raise ValueError('Missing or duplicate publication identity')
        source = article.find('./MedlineCitation/Article')
        if source is None:
            raise ValueError('Missing article metadata')
        dates = []
        for node in source.findall('./ArticleDate') + source.findall('./Journal/JournalIssue/PubDate'):
            parts = [node.findtext(key) for key in ('Year', 'Month', 'Day')]
            if all(parts):
                try:
                    month = parts[1] if parts[1].isdigit() else str(datetime.strptime(parts[1], '%b').month)
                    dates.append(date(int(parts[0]), int(month), int(parts[2])).isoformat())
                except ValueError:
                    pass
        earliest = min(dates) if dates else None
        ncts = sorted(set(re.findall(r'\bNCT\d{8}\b', ' '.join(
            node.text or '' for node in source.findall('./DataBankList/DataBank/AccessionNumberList/AccessionNumber')))))
        types = [node.text for node in source.findall('./PublicationTypeList/PublicationType')]
        records[pmid] = {
            'pmid': pmid, 'sourceUrl': 'https://pubmed.ncbi.nlm.nih.gov/' + pmid + '/',
            'title': ''.join(source.find('ArticleTitle').itertext()) if source.find('ArticleTitle') is not None else '',
            'publicationDate': earliest, 'publicationDateStatus': 'EXACT_DAY_REPORTED' if earliest else 'IMPRECISE_OR_MISSING',
            'inCutoff': bool(earliest and earliest <= cutoff), 'publicationTypes': types,
            'indexedNctsUnreviewed': ncts,
            'relationshipStatus': 'INDEXED_NCT_LINK_ONLY_NOT_VERIFIED_TRIAL_REPORT',
            'originalBatchReceipt': clean, 'fullTextReceipt': None,
            'independentReviewStatus': 'NOT_ADJUDICATED',
        }
    return records


# Questions are tied to the registered disease; they are not inferred deficiencies.
ENDPOINT_QUESTIONS = {
 'ABVX': 'Reconcile remission components, central endoscopy, steroid exposure and durability in ulcerative colitis.',
 'ACHV': 'Check continuous abstinence windows, biochemical validation, missing participants and durability after treatment.',
 'AGIO': 'Keep haemoglobin response separate from vaso-occlusive events and patient benefit in sickle cell disease; distinguish phase-specific cohorts.',
 'AMLX': 'Check definitions of hypoglycaemic events, glucose thresholds, rescue treatment and post-bariatric population applicability.',
 'APMD': 'Assess AHI measurement and night-to-night variability; AHI changes alone do not demonstrate cardiovascular benefit.',
 'AXSM': 'Separate cataplexy frequency from daytime sleepiness; check diary completeness, withdrawal effects and durability.',
 'BLTE': 'Relate retinal lesion progression to visual function and patient importance in Stargardt disease.',
 'CAPR': 'Check motor-function interpretation against age, disease trajectory, corticosteroid background and functional importance.',
 'CLDX': 'Interpret urticaria symptom scores, responder definitions, rescue medication and durability.',
 'COGT': 'Reconcile progression assessment, censoring, subsequent therapy and survival versus symptom benefit in GIST.',
 'CORT': 'Examine withdrawal/enrichment, blood-pressure and glycaemic endpoints, background treatment and generalisability in hypercortisolism.',
 'CYTK': 'Relate exercise capacity and symptoms to meaningful change; reconcile obstructive versus non-obstructive disease and comparator effects.',
 'IMNM': 'Distinguish radiographic progression from pain/function and spontaneous disease stability in desmoid tumours.',
 'MIRM': 'Check itch measurement and disease-specific subgroup applicability; excluded cholestatic diseases cannot establish benefit in EXPAND.',
 'MLTX': 'Review hidradenitis lesion-response components, draining tunnels, pain, rescue treatment and durability.',
 'MLYS': 'Relate blood-pressure measurement and background adherence to meaningful benefit; short-term BP changes alone are not cardiovascular-outcome evidence.',
 'PHVS': 'Separate acute attack relief from prevention; check attack confirmation, rescue treatment and patient-reported timing.',
 'PRAX': 'Assess tremor-related daily function, rating reliability, missing data and magnitude of meaningful change.',
 'SRPT': 'Check exon-specific population, function and dystrophin endpoints separately; biomarker change alone does not establish functional benefit.',
 'SVRA': 'Relate gas-transfer physiology to dyspnoea/function and rescue lavage in autoimmune pulmonary alveolar proteinosis.',
 'URGN': 'Check complete-response ascertainment, durability, tumour-risk population and formulation-specific applicability.',
 'VERA': 'Distinguish proteinuria response from renal-function preservation and longer-term outcomes in IgA nephropathy.',
 'ZBIO': 'Check relapse adjudication, glucocorticoid tapering, organ heterogeneity and patient importance in IgG4-related disease.',
}


def validate_publications(trial, cutoff):
    leads = {s['url'] for s in trial['sourceDiscoveryPlan'] if s['sourceKind'] == 'PUBLICATION_REFERENCE'}
    seen = set()
    for item in trial.get('publicationResearch', []):
        pmid = item['pmid']
        if (not re.fullmatch(r'\d+', pmid) or pmid in seen
                or item['sourceUrl'] != 'https://pubmed.ncbi.nlm.nih.gov/' + pmid + '/'
                or item['sourceUrl'] not in leads
                or item['relationshipStatus'] != 'INDEXED_NCT_LINK_ONLY_NOT_VERIFIED_TRIAL_REPORT'
                or item['independentReviewStatus'] != 'NOT_ADJUDICATED'):
            raise ValueError('Publication identity, duplicate or certification mismatch')
        seen.add(pmid)
        published = date.fromisoformat(item['publicationDate']) if item['publicationDate'] else None
        if item['inCutoff'] != bool(published and published <= date.fromisoformat(cutoff)):
            raise ValueError('Publication date/cutoff mismatch')
        for receipt in [item['originalBatchReceipt']] + ([item['fullTextReceipt']] if item.get('fullTextReceipt') else []):
            timestamp = datetime.fromisoformat(receipt['retrievedAt'].replace('Z', '+00:00'))
            if (timestamp.tzinfo is None or timestamp.astimezone(timezone.utc).date() > date.fromisoformat(cutoff)
                    or receipt['evidenceCutoffDate'] != cutoff or receipt['state'] != 'HASH_CHECKED'
                    or receipt['provenanceIndependentlyAuthenticated'] is not False
                    or receipt['independentlyScientificallyReviewed'] is not False
                    or not re.fullmatch(r'[0-9a-f]{64}', receipt['documentSha256'])):
                raise ValueError('Publication receipt cutoff or certification mismatch')
        if item.get('fullTextReceipt') and item['fullTextReceipt'].get('boundPmidUnreviewed') != pmid:
            raise ValueError('Cross-publication full-text binding')


def enrich(research, pdf_attempts, publications):
    """Produce six separate conservative research interpretations per trial."""
    result = copy.deepcopy(research)
    preparation().validate_snapshot(result, [t['nct'] for t in result['trials']])
    ncts = {t['nct'] for t in result['trials']}
    if any(row['nct'] not in ncts for row in pdf_attempts):
        raise ValueError('Document outside FOCUS')
    for trial in result['trials']:
        nct = trial['nct']; source = trial['registrySource']
        if source is None:
            raise ValueError('Registry source required for this current-source research report')
        attempts = [x for x in pdf_attempts if x['nct'] == nct]
        leads = {x['url'] for x in trial['sourceDiscoveryPlan'] if x.get('url')}
        documents = {}
        for item in attempts:
            if 'receipt' not in item:
                continue
            receipt = copy.deepcopy(item['receipt'])
            if receipt['nct'] != nct or receipt['sourceUrl'] not in leads:
                raise ValueError('Cross-trial document substitution')
            identity = (receipt['sourceUrl'], receipt['documentSha256'])
            if identity in documents:
                raise ValueError('Duplicate document receipt')
            documents[identity] = receipt
        trial['additionalOriginalDocuments'] = list(documents.values())
        retrieved_urls = {receipt['sourceUrl'] for receipt in documents.values()}
        for lead in trial['sourceDiscoveryPlan']:
            if lead.get('url') in retrieved_urls:
                lead.update(state='HASH_CHECKED', retrieved=True)
        trial['documentRetrievalFailures'] = [x for x in attempts if 'receipt' not in x]
        pmids = {x['url'].rstrip('/').split('/')[-1] for x in trial['sourceDiscoveryPlan'] if x['sourceKind'] == 'PUBLICATION_REFERENCE'}
        trial['publicationResearch'] = [copy.deepcopy(publications[p]) for p in sorted(pmids) if p in publications]
        validate_publications(trial, result['evidenceCutoffDate'])
        protocol = any(x['sourceKind'] in ('PROTOCOL', 'PROTOCOL_AND_SAP') for x in documents.values())
        sap = any(x['sourceKind'] in ('STATISTICAL_ANALYSIS_PLAN', 'PROTOCOL_AND_SAP') for x in documents.values())
        results = source['registryResultsContentPresent']
        endpoint_question = ENDPOINT_QUESTIONS.get(trial['ticker'], 'Require disease-specialist endpoint interpretation.')
        for level in trial['levels']:
            number = level['level']
            level['evidenceActuallyCollected'] = [{'sourceUrl': source['sourceUrl'], 'documentSha256': source['documentSha256'],
                'sourceKind': 'REGISTRY', 'publicationDateUnreviewed': source.get('registryPostedVersionDateUnreviewed')}]
            if number in (1,4,5):
                level['evidenceActuallyCollected'] += [{'sourceUrl': x['sourceUrl'], 'documentSha256': x['documentSha256'],
                    'sourceKind': x['sourceKind'], 'publicationDateUnreviewed': x.get('registryDeclaredDocumentDateUnreviewed')}
                    for x in documents.values()]
            level['preliminaryResearchInterpretation'] = {
                1: 'Original registry bytes and registered document receipts support traceability. Source ownership, exact document identity and authenticity remain unauthenticated.',
                2: 'Use the registry-listed phase, indication and eligibility for this research only; current identity and application-cycle relationships require independent reconciliation.',
                3: ('Posted primary-outcome fields permit descriptive research, not a trial-success judgment. Reconcile denominators, groups, uncertainty, harms and original reports.' if results else
                    'Abstain from efficacy conclusions: this packet has no posted structured results. A registered endpoint is a planned measure, not a demonstrated result.'),
                4: ('A registered protocol was retrieved; compare actual amendments and conduct with the registered design before judging execution.' if protocol else
                    'Registered design supports planning questions only; original protocol/amendment completeness and execution remain unresolved.'),
                5: ('A registered SAP was retrieved; its prespecification, amendments, estimands, multiplicity, missing data and reported analyses require statistical review.' if sap else
                    'Abstain from statistical adequacy/significance conclusions: no registered original SAP was retrieved for this trial.'),
                6: endpoint_question,
            }[number]
            level['supportingReasons'] = [
                'Exact-NCT registry receipt is retained at the stated current-source cutoff.',
                'Interpretation is bounded by collected evidence and does not certify efficacy or scientific adequacy.']
            level['riskFactorsRequiringReview'] = [endpoint_question,
                'Selective reporting, missing data and protocol/SAP amendment timing must be investigated; no deficiency is established by this question.']
            level['outstandingSourceQuestions'] = [
                'Reconcile original document versions, publication dates, registry amendments and protocol/SAP timing against unblinding/database lock.',
                'PubMed references may be background, prior-phase, secondary or protocol articles; NCT indexing alone does not establish a primary trial report.',
                'Document availability is unknown where retrieval failed; do not equate access failure with nonpublic evidence.']
            level['missingEvidence'] = ([name for name, present in [('original_protocol', protocol), ('original_SAP', sap), ('posted_registry_results', results)] if not present]
                + ['independent_source_authentication', 'qualified_clinical_statistical_review', 'independent_challenge_and_adjudication'])
            level['notYetExpectedEvidence'] = [x['requirement'] for x in level['requiredEvidence'] if x['state'] == 'NOT_YET_EXPECTED']
            level['nonpublicEvidence'] = []
            level['nonpublicAvailabilityStatus'] = 'NOT_ESTABLISHED_DO_NOT_INFER_FROM_RETRIEVAL_FAILURE'
            level['sourceAvailabilityNote'] = 'Current-phase missing documents are collection gaps, not automatic scientific deficiencies or evidence of nonpublic status.'
    preparation().validate_snapshot(result, sorted(ncts))
    return result


def coverage(research):
    rows = preparation().validate_snapshot(research, [t['nct'] for t in research['trials']])
    output = []
    all_documents = set()
    for nct, trial in rows.items():
        validate_publications(trial, research['evidenceCutoffDate'])
        fda = trial.get('fdaExactNctSearch', {})
        if fda:
            if fda.get('nct') != nct or fda.get('relationshipVerified') is not False:
                raise ValueError('FDA search identity or unsupported verification')
            for match in fda.get('labelMatchesUnreviewed', []):
                effective = match.get('effectiveTime', '')
                if (match.get('exactNctTextPresent') is not True or not re.fullmatch(r'\d{8}', effective)
                        or datetime.strptime(effective, '%Y%m%d').date() > date.fromisoformat(research['evidenceCutoffDate'])):
                    raise ValueError('FDA label identity or version beyond cutoff')
        documents = trial.get('additionalOriginalDocuments', [])
        for receipt in documents + ([trial['registrySource']] if trial['registrySource'] else []):
            declared = receipt.get('registryDeclaredDocumentDateUnreviewed')
            if declared and date.fromisoformat(declared) > date.fromisoformat(research['evidenceCutoffDate']):
                raise ValueError('Declared original document date exceeds cutoff')
            all_documents.add(receipt['documentSha256'])
        publications = [p for p in trial.get('publicationResearch', []) if p['inCutoff']]
        output.append({'nct': nct, 'ticker': trial['ticker'], 'company': trial['company'],
            'indicationUnreviewed': trial['registrySource']['indicationsUnreviewed'],
            'phaseUnreviewed': trial['registrySource']['phasesUnreviewed'],
            'registry': bool(trial['registrySource']),
            'protocol': any(d['sourceKind'] in ('PROTOCOL','PROTOCOL_AND_SAP') for d in documents),
            'sap': any(d['sourceKind'] in ('STATISTICAL_ANALYSIS_PLAN','PROTOCOL_AND_SAP') for d in documents),
            'postedResults': trial['registrySource']['registryResultsContentPresent'],
            'indexedJournalRecords': len(publications),
            'retrievedPublicFullTexts': sum(bool(p.get('fullTextReceipt')) for p in publications),
            'exactNctFdaLabelPackets': bool(trial.get('fdaExactNctSearch', {}).get('labelMatchesUnreviewed')),
            'verifiedPeerReviewedTrialReports': 0,
            'exactTrialFdaDocumentsVerified': 0,
            'preliminaryLevels': sum(bool(l['preliminaryFindings']) and bool(l.get('preliminaryResearchInterpretation')) for l in trial['levels']),
            'mappingStatus': trial['mappingStatus'],
            'independentSources': 0, 'independentlyAdjudicatedAssessments': 0,
            'awaitingAdditionalEvidence': True, 'blockedOnIndependentReview': True})
    keys = ('registry','protocol','sap','postedResults','indexedJournalRecords','retrievedPublicFullTexts','exactNctFdaLabelPackets')
    return {'kind': 'LEVEL16_SCIENTIFIC_COVERAGE_NOT_EVIDENCE_COMPLETENESS', 'evidenceCutoffDate': research['evidenceCutoffDate'],
        'focusTrialCount': len(output), 'trialCoverageCounts': {key: sum(bool(row[key]) for row in output) for key in keys},
        'trialsWithSixPreliminaryLevels': sum(row['preliminaryLevels'] == 6 for row in output),
        'awaitingAdditionalEvidence': len(output), 'blockedOnIndependentReview': len(output),
        'uniqueRegistryAndProtocolSapOriginals': len(all_documents),
        'verifiedPeerReviewedTrialReports': 0, 'verifiedExactTrialFdaDocuments': 0,
        'independentlyAuthenticatedSources': 0, 'independentlyAdjudicatedAssessments': 0,
        'historicalPredictionInputPermitted': False, 'approvalProbability': None,
        'limitations': ['Registry coverage is not scientific evidence completeness.',
            'Indexed publication/full-text counts are discovery/collection counts, not independently verified trial-report counts.',
            'FDA product records and drug-level labels do not establish exact trial/application-cycle relationships.'], 'trials': output}


def markdown(report):
    lines = ['# Scientific coverage — preliminary, unreviewed', '',
        'Current-source research only. Zero independent source authentications and zero adjudicated assessments. Not a blind prediction input.', '',
        'Trial coverage: ' + '; '.join(key + ': ' + str(value) + '/32' for key, value in report['trialCoverageCounts'].items()) + '.', '',
        '| NCT | Ticker | Phase (unreviewed) | Registry | Protocol | SAP | Posted results | Indexed journal records | Public full texts | Exact-NCT FDA label packet | Preliminary levels |',
        '|---|---|---|---|---|---|---|---|---|---|---|']
    for row in report['trials']:
        lines.append('| ' + ' | '.join(str(x) for x in (row['nct'],row['ticker'],','.join(row['phaseUnreviewed']),
            row['registry'],row['protocol'],row['sap'],row['postedResults'],row['indexedJournalRecords'],row['retrievedPublicFullTexts'],row['exactNctFdaLabelPackets'],row['preliminaryLevels'])) + ' |')
    lines += ['', 'All 32 trials await additional evidence and independent review. Unmapped application exceptions remain NCT05031780, NCT06747468 and NCT06553768.', '', *report['limitations'], '']
    return '\n'.join(lines)


if __name__ == '__main__':
    import argparse
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--research', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = coverage(json.loads(args.research.read_text(encoding='utf-8')))
    # Never overwrite an existing research/history artifact.
    with args.output.open('x', encoding='utf-8') as handle:
        handle.write(json.dumps(report, indent=2, ensure_ascii=False) + '\n')

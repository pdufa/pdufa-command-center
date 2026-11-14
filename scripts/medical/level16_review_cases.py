"""Offline source-verification dossiers and scientific-review proposals.

These are untrusted intake records, not authenticated review events. No identity
provider, permissioned reviewer store, or adjudicator is connected here; therefore
there is deliberately no path to VERIFIED or independently reviewed output.
"""
from datetime import date
import re

STATES = frozenset({'UNREVIEWED', 'MISSING', 'CONFLICTING',
                    'NOT_YET_EXPECTED_AT_THIS_PHASE', 'NOT_PUBLICLY_AVAILABLE'})
CHECKS = ('exactNct', 'phase', 'registryStatus', 'indication', 'population',
          'sourceOwnership', 'publicationDate', 'retrievalDate',
          'documentVersion', 'protocolVersion')
PHASES = frozenset({'EARLY_PHASE1', 'PHASE1', 'PHASE2', 'PHASE3', 'PHASE4', 'NA'})


def _text(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 4000:
        raise ValueError('Expected bounded nonblank text')
    return value.strip()


def _date(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise ValueError('Expected ISO calendar date')
    return date.fromisoformat(value)


def _texts(value):
    if not isinstance(value, list) or len(value) > 100:
        raise ValueError('Expected bounded text list')
    return [_text(x) for x in value]


def _keys(value, expected):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise ValueError('Missing, unknown, or forbidden certification/prediction fields')


def _document(document, kind, cutoff):
    _keys(document, ('schemaVersion', 'kind', 'cutoffDate', 'records'))
    if type(document['schemaVersion']) is not int or document['schemaVersion'] != 1 or document['kind'] != kind:
        raise ValueError('Unsupported review-case schema')
    if _date(document['cutoffDate']) != _date(cutoff):
        raise ValueError('Review cases must use the source-submission evidence cutoff')
    rows = document['records']
    if not isinstance(rows, list) or len(rows) > 2000:
        raise ValueError('Expected bounded review-case records')
    return rows


def prepare(submissions_by_nct, cutoff, source_cases=None, review_proposals=None):
    """Bind dossiers/proposals to validated source leads without promoting them.

    Evidence cutoff applies to the evidence bundle. Review dates may be later;
    this never establishes a blind prospective assessment or prediction.
    """
    sources = {}
    for nct, rows in submissions_by_nct.items():
        for source in rows:
            ident = source['submissionId']
            if ident in sources:
                raise ValueError('Duplicate validated source ID')
            sources[ident] = (nct, source)
    dossiers, proposals, seen = {}, {}, set()
    if source_cases is not None:
        for row in _document(source_cases, 'FOCUS_LEVELS_1_6_SOURCE_CASES', cutoff):
            _keys(row, ('submissionId', 'nct', 'documentSha256', 'sourceUrl',
                        'sourceDate', 'accessedDate', 'candidateApplicationCycleId',
                        'checks', 'conflicts', 'limitations'))
            ident = row['submissionId']
            if not isinstance(ident, str) or ident not in sources or ident in dossiers:
                raise ValueError('Unknown or duplicate source-case ID')
            nct, source = sources[ident]
            if row['nct'] != nct or any(row[key] != source[key] for key in (
                    'sourceUrl', 'sourceDate', 'accessedDate', 'candidateApplicationCycleId')):
                raise ValueError('Source case changed exact trial/application or acquisition identity')
            if row['documentSha256'] != source['submittedDigestUnverified']:
                raise ValueError('Source case changed original document digest')
            _keys(row['checks'], CHECKS)
            checks = {}
            for key, item in row['checks'].items():
                _keys(item, ('state', 'observation', 'locator'))
                state = item['state']
                if not isinstance(state, str) or state not in STATES:
                    raise ValueError('A source case cannot certify verification')
                if state == 'NOT_YET_EXPECTED_AT_THIS_PHASE':
                    raise ValueError('Provenance and identity checks cannot be waived by phase')
                checks[key] = {'state': state, 'observation': _text(item['observation']),
                               'locator': _text(item['locator'])}
            conflicts = _texts(row['conflicts'])
            if any(x['state'] == 'CONFLICTING' for x in checks.values()) and not conflicts:
                raise ValueError('Conflicting checks require explicit contradictory information')
            blockers = ['AUTHENTICATED_SOURCE_REVIEW_REQUIRED', 'TRUSTED_REVIEWER_IDENTITY_REQUIRED']
            blockers += [key + ':' + item['state'] for key, item in checks.items()
                         if item['state'] != 'UNREVIEWED']
            if conflicts:
                blockers.append('SOURCE_CONFLICT_RECONCILIATION_REQUIRED')
            receipt = source.get('localByteReceipt', {})
            if receipt.get('byteMatchStatus') != 'LOCAL_BYTES_MATCH_SUBMITTED_DIGEST_ONLY':
                blockers.append('ORIGINAL_DOCUMENT_BYTE_MATCH_REQUIRED')
            duplicates = sorted(other_id for other_id, (_, other) in sources.items()
                                if other_id != ident and other['submittedDigestUnverified'] == source['submittedDigestUnverified'])
            variants = sorted(other_id for other_id, (_, other) in sources.items()
                              if other_id != ident and other['sourceUrl'] == source['sourceUrl']
                              and other['submittedDigestUnverified'] != source['submittedDigestUnverified'])
            if duplicates:
                blockers.append('DUPLICATE_DOCUMENT_NOT_INDEPENDENT_CORROBORATION')
            if variants:
                blockers.append('SOURCE_DOCUMENT_VARIANTS_REQUIRE_RECONCILIATION')
            dossiers[ident] = {
                'status': 'SOURCE_CASE_UNREVIEWED', 'checks': checks,
                'sameDigestSubmissionIds': duplicates, 'sameUrlDifferentDigestSubmissionIds': variants,
                'conflicts': conflicts, 'limitations': _texts(row['limitations']),
                'blockers': blockers, 'independentlyAuthenticated': False,
            }
    if review_proposals is not None:
        for row in _document(review_proposals, 'FOCUS_LEVELS_1_6_REVIEW_PROPOSALS', cutoff):
            _keys(row, ('proposalId', 'nct', 'level', 'candidateApplicationCycleId',
                        'sourceSubmissionIds', 'phaseBasis', 'evidenceState',
                        'findings', 'reasons', 'contradictoryEvidence', 'limitations',
                        'reviewerIdentityClaim', 'reviewDate', 'challenge', 'outstandingBlockers'))
            ident = _text(row['proposalId'])
            if ident in seen:
                raise ValueError('Duplicate review proposal ID')
            seen.add(ident)
            nct, level = row['nct'], row['level']
            if not isinstance(nct, str) or nct not in submissions_by_nct or type(level) is not int or not 1 <= level <= 6:
                raise ValueError('Review proposal outside exact FOCUS Levels 1–6')
            ids = _texts(row['sourceSubmissionIds'])
            if not ids or len(set(ids)) != len(ids):
                raise ValueError('Review proposals need unique exact evidence links')
            for source_id in ids:
                if source_id not in sources:
                    raise ValueError('Unknown review evidence')
                source_nct, source = sources[source_id]
                if source_nct != nct or source['level'] != level or source['candidateApplicationCycleId'] != row['candidateApplicationCycleId']:
                    raise ValueError('Review evidence trial/level/application mismatch')
                if _date(row['reviewDate']) < _date(source['accessedDate']):
                    raise ValueError('Review predates evidence retrieval')
            phase = row['phaseBasis']
            if not isinstance(phase, list) or not phase or any(not isinstance(x, str) or x not in PHASES for x in phase) or len(set(phase)) != len(phase):
                raise ValueError('Explicit phase basis is required before scientific review')
            state = row['evidenceState']
            if not isinstance(state, str) or state not in STATES:
                raise ValueError('Review proposals cannot certify evidence')
            if state == 'NOT_YET_EXPECTED_AT_THIS_PHASE' and (level not in (3, 5) or not set(phase) <= {'EARLY_PHASE1', 'PHASE1', 'PHASE2'}):
                raise ValueError('Phase waiver limited to early-phase results/statistics')
            challenge = row['challenge']
            _keys(challenge, ('reviewerIdentityClaim', 'reviewDate', 'findings', 'limitations'))
            challenge_result = None
            if any(value is not None for value in challenge.values()):
                if _text(challenge['reviewerIdentityClaim']) == _text(row['reviewerIdentityClaim']):
                    raise ValueError('Self-challenge is not an independent second review')
                if _date(challenge['reviewDate']) < _date(row['reviewDate']):
                    raise ValueError('Challenge predates proposed review')
                challenge_result = {
                    'reviewerIdentityClaim': _text(challenge['reviewerIdentityClaim']),
                    'reviewDate': challenge['reviewDate'], 'findings': _texts(challenge['findings']),
                    'limitations': _texts(challenge['limitations']), 'status': 'IDENTITY_AND_CHALLENGE_UNVERIFIED'}
            contradictions = _texts(row['contradictoryEvidence'])
            if state == 'CONFLICTING' and not contradictions:
                raise ValueError('Conflicting review requires contradictory evidence')
            if not _texts(row['findings']) or not _texts(row['reasons']) or not _texts(row['limitations']):
                raise ValueError('Proposed findings require reasons and explicit limitations')
            proposal = {
                'proposalId': ident, 'status': 'UNREVIEWED_PROPOSAL_NOT_SCIENTIFIC_ASSESSMENT',
                'candidateApplicationCycleId': row['candidateApplicationCycleId'],
                'sourceSubmissionIds': ids, 'phaseBasisUnverified': phase,
                'evidenceStateUnverified': state,
                'findingsUnreviewed': _texts(row['findings']), 'reasonsUnreviewed': _texts(row['reasons']),
                'contradictoryEvidence': contradictions, 'limitations': _texts(row['limitations']),
                'reviewerIdentityClaim': _text(row['reviewerIdentityClaim']),
                'reviewDate': _date(row['reviewDate']).isoformat(), 'challenge': challenge_result,
                'blockers': _texts(row['outstandingBlockers']) + [
                    'TRUSTED_REVIEWER_IDENTITY_REQUIRED', 'INDEPENDENT_SCIENTIFIC_ADJUDICATION_REQUIRED',
                    'ORIGINAL_SOURCE_AUTHENTICATION_REQUIRED', 'PHASE_BASIS_VERIFICATION_REQUIRED'],
                'independentlyReviewed': False, 'prospectiveBlindAssessment': False,
            }
            if challenge_result is None:
                proposal['blockers'].append('INDEPENDENT_CHALLENGE_REQUIRED')
            proposals.setdefault(nct, {}).setdefault(level, []).append(proposal)
    return dossiers, proposals

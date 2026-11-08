"""Reject retired scoring inputs at active prediction-write boundaries.

This is a prohibition, not a scoring dependency. Historical prediction and
assessment documents remain unchanged and readable; this guard is never run to
rewrite them. Active scientific evidence must establish its own provenance.
"""
from __future__ import annotations

import re
from collections.abc import Mapping

_RETIRED_MODEL_MARKERS = (
    'raas', 'clinical_five', 'clinical-five', 'postdata_five_factor',
    'bottom_only_post_readout', 'top_only_pre_readout',
)
_MODEL_FIELDS = frozenset({
    'model', 'modelname', 'modelversion', 'scorekind', 'scoretype',
    'scoringsystem', 'framework', 'algorithm', 'derivedfrom', 'inputmodel',
    'evidencemodel', 'sourcemodel', 'sourcetype', 'sourcekind', 'scoreversion',
    'assessmenttype', 'inputsource', 'assessmentmodel', 'scientificreadiness',
    'readinesssource', 'confidencebasis', 'certaintybasis',
})


def reject_retired_analysis_payload(payload: Mapping) -> None:
    """Reject explicit retired models/inputs without mining source prose.

    A regulatory source may describe historical systems in ordinary prose.
    Only structured input keys, declared model/basis fields and evidence IDs
    establish an attempted active dependency. Unknown evidence still has to pass
    the independent existing exact-application/source validation downstream.
    """
    pending = [payload]
    while pending:
        item = pending.pop()
        if isinstance(item, Mapping):
            for key, value in item.items():
                normalized = re.sub(r'[^a-z0-9]', '', str(key).lower())
                if normalized.startswith('raas'):
                    raise ValueError('Permanently retired analysis inputs are prohibited')
                if normalized in _MODEL_FIELDS and isinstance(value, str):
                    if any(marker in value.lower() for marker in _RETIRED_MODEL_MARKERS):
                        raise ValueError('Permanently retired scoring models cannot produce FDA predictions or certainty')
                if normalized in {'evidenceids', 'inputids'} and isinstance(value, (list, tuple)):
                    if any(isinstance(eid, str) and eid.lower().startswith(('raas:', 'raas-', 'raas_')) for eid in value):
                        raise ValueError('Retired score records are not active scientific evidence')
                if isinstance(value, (Mapping, list, tuple)):
                    pending.append(value)
        elif isinstance(item, (list, tuple)):
            pending.extend(value for value in item if isinstance(value, (Mapping, list, tuple)))

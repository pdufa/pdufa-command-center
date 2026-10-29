"""Server-controlled research account and program grants; never token claims.

The hosting process supplies this directory or an explicitly managed local file.
There is no HTTP enrollment/grant endpoint and no automatic role provisioning.
Multiple external identities may map to one canonical principal so aliases do
not bypass the independent-review restriction.
"""
from __future__ import annotations
from dataclasses import dataclass
import json
from pathlib import Path
from threading import RLock
from types import MappingProxyType
from urllib.parse import urlsplit

from research.prediction_v1_1_authorization import ResearchPrincipal
from research.prediction_v1_1_oidc_verifier import VerifiedIdentity


@dataclass(frozen=True)
class _Account:
    principal: ResearchPrincipal
    active: bool


def _nonempty(value, name):
    if (not isinstance(value, str) or not value or value != value.strip()
            or len(value) > 2000 or any(ord(c) < 32 for c in value)):
        raise ValueError(f'canonical server-owned {name} required')
    return value


def _accounts(records):
    if not isinstance(records, (list, tuple)):
        raise ValueError('explicit server-owned account records required')
    result = {}
    fields = {'issuer', 'subject', 'principal', 'roles', 'program_ids', 'active'}
    for record in records:
        if not isinstance(record, dict) or set(record) != fields:
            raise ValueError('exact server-owned account fields required')
        issuer = _nonempty(record['issuer'], 'issuer')
        subject = _nonempty(record['subject'], 'subject')
        try:
            parsed = urlsplit(issuer)
            valid = (parsed.scheme == 'https' and parsed.hostname and not parsed.username
                     and not parsed.password and not parsed.query and not parsed.fragment
                     and parsed.port in (None, 443))
        except ValueError:
            valid = False
        if not valid:
            raise ValueError('canonical trusted issuer required')
        if type(record['active']) is not bool:
            raise ValueError('explicit server-owned account activation required')
        for field in ('roles', 'program_ids'):
            values = record[field]
            if (not isinstance(values, (list, tuple, set, frozenset))
                    or any(not isinstance(v, str) for v in values)
                    or len(set(values)) != len(values)):
                raise ValueError('explicit unique server-owned grants required')
        principal = ResearchPrincipal(record['principal'], frozenset(record['roles']),
                                      frozenset(record['program_ids']))
        key = (issuer, subject)
        if key in result:
            raise ValueError('duplicate issuer/subject binding')
        result[key] = _Account(principal, record['active'])
    return MappingProxyType(result)


class PrincipalDirectory:
    """Immutable grant snapshots, replaceable only by trusted hosting code."""
    def __init__(self, records):
        self._lock = RLock()
        self._accounts = _accounts(records)

    def replace(self, records):
        """Apply server-side grant/revocation changes atomically, no HTTP path."""
        replacement = _accounts(records)
        with self._lock:
            self._accounts = replacement

    @classmethod
    def from_file(cls, path):
        """Read an explicitly configured, operator-owned file; never a client path."""
        def unique(pairs):
            out = {}
            for key, value in pairs:
                if key in out:
                    raise ValueError('duplicate account directory field')
                out[key] = value
            return out
        data = json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=unique)
        if not isinstance(data, dict) or set(data) != {'schema_version', 'accounts'} or data['schema_version'] != 'research-principal-directory-v1':
            raise ValueError('versioned server-owned principal directory required')
        return cls(data['accounts'])

    def resolve(self, identity):
        if type(identity) is not VerifiedIdentity:
            raise PermissionError('cryptographically verified external identity required')
        with self._lock:
            account = self._accounts.get((identity.issuer, identity.subject))
        if account is None or not account.active:
            raise PermissionError('research account is absent or disabled')
        return account.principal

"""Trusted principal and program-scope contract for future v1.1 backend.

This does NOT authenticate credentials. Only a future verified authentication
provider may construct principals; do not deserialize this from client JSON.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import FrozenSet


@dataclass(frozen=True)
class ResearchPrincipal:
    principal: str
    roles: FrozenSet[str]
    program_ids: FrozenSet[str]
    is_authenticated: bool = True


def authorize_research_read(principal, program_id: str):
    """Fail closed for absent, malformed, or insufficient caller identity."""
    if not isinstance(principal, ResearchPrincipal):
        raise PermissionError("trusted principal required")
    if not principal.is_authenticated or not principal.principal.strip():
        raise PermissionError("authenticated principal required")
    if "evidence_reader" not in principal.roles:
        raise PermissionError("evidence reader role required")
    if not isinstance(program_id, str) or not program_id.strip() or program_id not in principal.program_ids:
        raise PermissionError("program-scoped access denied")
    return True


def authorize_research_review(principal, program_id: str, submitter_principal: str):
    """Reviewers must have explicit program access and differ from submitters."""
    if not isinstance(principal, ResearchPrincipal):
        raise PermissionError("trusted principal required")
    if not principal.is_authenticated or not principal.principal.strip():
        raise PermissionError("authenticated principal required")
    if "evidence_reviewer" not in principal.roles or program_id not in principal.program_ids:
        raise PermissionError("reviewer role and program access required")
    if not isinstance(submitter_principal, str) or not submitter_principal.strip():
        raise PermissionError("verified submitter identity required")
    if principal.principal == submitter_principal:
        raise PermissionError("self-review forbidden")
    return True

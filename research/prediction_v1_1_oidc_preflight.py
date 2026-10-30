"""Fail-closed research identity-provider configuration preflight.

This is a configuration contract only. It does not verify JWT signatures,
perform login, provision roles, or authorize any production HTTP endpoint.
"""
from dataclasses import dataclass
import ipaddress
import re
import unicodedata
from urllib.parse import urlsplit

class IdentityProviderNotConfigured(RuntimeError):
    pass

@dataclass(frozen=True)
class OIDCConfiguration:
    issuer: str
    audience: str
    jwks_uri: str


def _unsafe_characters(value):
    return any(c.isspace() or unicodedata.category(c).startswith("C") for c in value)


def _provider_url(label, value):
    """Validate a configured public DNS URL, without resolving or fetching it.

    Explicit provider configuration remains a server trust decision. Syntax
    checks cannot establish who controls a hostname or where DNS resolves.
    """
    if (not isinstance(value, str) or not value or len(value) > 2048
            or _unsafe_characters(value)
            or "\\" in value or "?" in value or "#" in value
            or re.search(r"%(?:0[0-9a-f]|1[0-9a-f]|7f)", value, re.IGNORECASE)):
        raise IdentityProviderNotConfigured(f"{label} must be a clean HTTPS URL")
    try:
        parsed = urlsplit(value)
        host, port = parsed.hostname, parsed.port
    except ValueError as exc:
        raise IdentityProviderNotConfigured(f"{label} invalid") from exc
    if (parsed.scheme != "https" or not host
            or parsed.username is not None or parsed.password is not None
            or port not in (None, 443) or parsed.netloc.endswith(":")):
        raise IdentityProviderNotConfigured(f"{label} must be a clean HTTPS URL")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise IdentityProviderNotConfigured(f"{label} requires an explicit public DNS hostname")
    labels = host.split(".")
    if (len(host) > 253 or len(labels) < 2
            or any(not re.fullmatch(r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?", part)
                   for part in labels)
            or not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9-]*", labels[-1])
            or host == "localhost" or host.endswith((".localhost", ".local", ".internal", ".lan", ".home", ".home.arpa"))):
        raise IdentityProviderNotConfigured(f"{label} requires an explicit public DNS hostname")
    return parsed


def validate_oidc_configuration(config):
    if not isinstance(config, OIDCConfiguration):
        raise IdentityProviderNotConfigured("Trusted OIDC configuration missing")
    issuer,audience,jwks=config.issuer,config.audience,config.jwks_uri
    if (not isinstance(audience,str) or not audience or len(audience) > 2048
            or _unsafe_characters(audience)):
        raise IdentityProviderNotConfigured("Explicit token audience required")
    issuer_url = _provider_url("issuer", issuer)
    jwks_url = _provider_url("JWKS URI", jwks)
    if issuer_url.hostname != jwks_url.hostname:
        raise IdentityProviderNotConfigured("Issuer and JWKS hosts must match until a provider-specific trust policy is implemented")
    return config

def require_live_identity_verifier(*args,**kwargs):
    raise IdentityProviderNotConfigured("No cryptographically verified identity provider has been connected")

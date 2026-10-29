"""Fail-closed research identity-provider configuration preflight.

This is a configuration contract only. It does not verify JWT signatures,
perform login, provision roles, or authorize any production HTTP endpoint.
"""
from dataclasses import dataclass
from urllib.parse import urlsplit

class IdentityProviderNotConfigured(RuntimeError):
    pass

@dataclass(frozen=True)
class OIDCConfiguration:
    issuer: str
    audience: str
    jwks_uri: str

def validate_oidc_configuration(config):
    if not isinstance(config, OIDCConfiguration):
        raise IdentityProviderNotConfigured("Trusted OIDC configuration missing")
    issuer,audience,jwks=config.issuer,config.audience,config.jwks_uri
    if not isinstance(audience,str) or not audience.strip():
        raise IdentityProviderNotConfigured("Explicit token audience required")
    for label,value in (("issuer",issuer),("JWKS URI",jwks)):
        if not isinstance(value,str):
            raise IdentityProviderNotConfigured(f"{label} missing")
        try:
            parsed=urlsplit(value)
        except ValueError as exc:
            raise IdentityProviderNotConfigured(f"{label} invalid") from exc
        if parsed.scheme!="https" or not parsed.hostname or parsed.username or parsed.password or parsed.fragment or parsed.query:
            raise IdentityProviderNotConfigured(f"{label} must be a clean HTTPS URL")
        if parsed.hostname in ("localhost","127.0.0.1","::1"):
            raise IdentityProviderNotConfigured(f"{label} must not use localhost")
    if urlsplit(issuer).hostname != urlsplit(jwks).hostname:
        raise IdentityProviderNotConfigured("Issuer and JWKS hosts must match until a provider-specific trust policy is implemented")
    return config

def require_live_identity_verifier(*args,**kwargs):
    raise IdentityProviderNotConfigured("No cryptographically verified identity provider has been connected")

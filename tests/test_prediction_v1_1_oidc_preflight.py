import unittest
from research.prediction_v1_1_oidc_preflight import OIDCConfiguration,IdentityProviderNotConfigured,validate_oidc_configuration,require_live_identity_verifier

class OIDCPreflightTests(unittest.TestCase):
 def test_valid_configuration_is_only_configuration(self):
  config=OIDCConfiguration("https://identity.example.org/","pdufa-evidence","https://identity.example.org/keys")
  self.assertEqual(validate_oidc_configuration(config),config)
  with self.assertRaises(IdentityProviderNotConfigured):require_live_identity_verifier(config)
 def test_missing_audience_denied(self):
  with self.assertRaises(IdentityProviderNotConfigured):
   validate_oidc_configuration(OIDCConfiguration("https://identity.example.org/","","https://identity.example.org/keys"))
 def test_http_issuer_denied(self):
  with self.assertRaises(IdentityProviderNotConfigured):
   validate_oidc_configuration(OIDCConfiguration("http://identity.example.org/","aud","https://identity.example.org/keys"))
 def test_cross_host_jwks_denied(self):
  with self.assertRaises(IdentityProviderNotConfigured):
   validate_oidc_configuration(OIDCConfiguration("https://identity.example.org/","aud","https://attacker.example.org/keys"))
 def test_localhost_denied(self):
  with self.assertRaises(IdentityProviderNotConfigured):
   validate_oidc_configuration(OIDCConfiguration("https://localhost/","aud","https://localhost/keys"))
 def test_query_string_denied(self):
  with self.assertRaises(IdentityProviderNotConfigured):
   validate_oidc_configuration(OIDCConfiguration("https://identity.example.org/?x=1","aud","https://identity.example.org/keys"))

if __name__=="__main__":unittest.main()

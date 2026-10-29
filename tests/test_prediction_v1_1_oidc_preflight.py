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

 def test_only_default_https_port_is_supported(self):
  for authority in ("identity.example.org:80", "identity.example.org:8443", "identity.example.org:notaport", "identity.example.org:", "identity.example.org:99999"):
   for field in ("issuer", "jwks_uri"):
    with self.subTest(authority=authority, field=field):
     config={"issuer":"https://identity.example.org/", "audience":"aud", "jwks_uri":"https://identity.example.org/keys"}
     config[field]="https://"+authority+"/keys"
     with self.assertRaises(IdentityProviderNotConfigured):validate_oidc_configuration(OIDCConfiguration(**config))
  config=OIDCConfiguration("https://identity.example.org:443/tenant", "api://pdufa-evidence", "https://identity.example.org/keys")
  self.assertEqual(validate_oidc_configuration(config),config)

 def test_ip_literals_and_nonpublic_hostname_forms_are_denied(self):
  for host in ("127.0.0.1", "10.0.0.1", "169.254.169.254", "8.8.8.8", "[::1]", "[2001:4860:4860::8888]", "2130706433", "0x7f000001", "auth.localhost", "auth.local", "auth.internal", "auth.lan", "auth.home", "router.home.arpa"):
   with self.subTest(host=host):
    with self.assertRaises(IdentityProviderNotConfigured):
     validate_oidc_configuration(OIDCConfiguration("https://"+host+"/", "aud", "https://"+host+"/keys"))

 def test_invalid_dns_names_are_denied(self):
  for host in ("identity", ".example.org", "identity..example.org", "-identity.example.org", "identity-.example.org", "identity_example.org", "identity.example.org.", "identity.example.123", "identity%2eexample.org", "a"*64+".example.org"):
   with self.subTest(host=host):
    with self.assertRaises(IdentityProviderNotConfigured):
     validate_oidc_configuration(OIDCConfiguration("https://"+host+"/", "aud", "https://"+host+"/keys"))

 def test_userinfo_fragments_empty_queries_and_backslashes_are_denied(self):
  for url in ("https://user:password@identity.example.org/", "https://@identity.example.org/", "https://identity.example.org/?", "https://identity.example.org/#", "https://identity.example.org/#fragment", "https://identity.example.org\\@attacker.example.org/", "https://identity.example.org/%0d%0aheader"):
   for field in ("issuer", "jwks_uri"):
    with self.subTest(url=url, field=field):
     config={"issuer":"https://identity.example.org/", "audience":"aud", "jwks_uri":"https://identity.example.org/keys"}
     config[field]=url
     with self.assertRaises(IdentityProviderNotConfigured):validate_oidc_configuration(OIDCConfiguration(**config))

 def test_whitespace_and_controls_are_denied_for_every_configuration_field(self):
  for unsafe in (" ", "\n", "\t", "\x00", "\x7f", "\x80", "\u202e", "\u200b"):
   for field in ("issuer", "audience", "jwks_uri"):
    with self.subTest(unsafe=repr(unsafe), field=field):
     config={"issuer":"https://identity.example.org/", "audience":"aud", "jwks_uri":"https://identity.example.org/keys"}
     config[field]+=unsafe
     with self.assertRaises(IdentityProviderNotConfigured):validate_oidc_configuration(OIDCConfiguration(**config))

 def test_configuration_fields_are_bounded_and_typed(self):
  for field in ("issuer", "audience", "jwks_uri"):
   for value in (None, False, "", "x"*2049):
    with self.subTest(field=field, value_type=type(value).__name__):
     config={"issuer":"https://identity.example.org/", "audience":"aud", "jwks_uri":"https://identity.example.org/keys"}
     config[field]=value
     with self.assertRaises(IdentityProviderNotConfigured):validate_oidc_configuration(OIDCConfiguration(**config))

if __name__=="__main__":unittest.main()

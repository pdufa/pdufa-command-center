import unittest
from scripts.pdufa_mail_count import collect, pdufa_folders, QUERY


class FakeIMAP:
    def __init__(self, *args, **kwargs):
        self.calls = []
        self.folder = None
        self.broken = False

    def login(self, *args):
        pass

    def list(self, reference, pattern):
        self.calls.append(("LIST", reference, pattern))
        return "OK", [b'(\\HasChildren) "/" "PDUFA"',
                      b'(\\HasNoChildren) "/" "PDUFA/Scan END"',
                      b'(\\HasNoChildren) "/" "INBOX"',
                      b'(\\HasNoChildren) "/" "PDUFA-other"']

    def select(self, folder, readonly=False):
        self.calls.append(("SELECT", folder, readonly))
        self.folder = folder
        return "OK", [b"2"]

    def uid(self, operation, *args):
        self.calls.append((operation,) + args)
        if operation == "SEARCH":
            return "OK", [b"1 2"]
        if self.broken:
            return "OK", [b"1 (UID 1 X-GM-MSGID 111 FLAGS ())"]
        if self.folder == b'"PDUFA"':
            return "OK", [b"1 (UID 1 X-GM-MSGID 111 FLAGS ())",
                          b"2 (UID 2 X-GM-MSGID 222 FLAGS (\\Seen))"]
        return "OK", [b"1 (UID 1 X-GM-MSGID 222 FLAGS (\\Seen))",
                      b"2 (UID 2 X-GM-MSGID 333 FLAGS ())"]

    def logout(self):
        self.calls.append(("LOGOUT",))


class MailCountTests(unittest.TestCase):
    def test_exact_deduplicated_counts_and_strict_readonly_scope(self):
        fake = FakeIMAP()
        result = collect("user", "password", imap_factory=lambda *a, **k: fake)
        self.assertEqual(result["status"], "CHECKED")
        self.assertEqual(result["total_count"], 3)
        self.assertEqual(result["unread_count"], 2)
        selections = [call for call in fake.calls if call[0] == "SELECT"]
        self.assertEqual(len(selections), 2)
        self.assertTrue(all(call[2] is True and call[1].startswith(b'"PDUFA') for call in selections))
        self.assertEqual(fake.calls[0], ("LIST", '""', '"PDUFA*"'))
        for call in fake.calls:
            self.assertIn(call[0], {"LIST", "SELECT", "SEARCH", "FETCH", "LOGOUT"})
            if call[0] == "SEARCH":
                self.assertEqual(call[-2:], ("X-GM-RAW", QUERY))
            if call[0] == "FETCH":
                self.assertEqual(call[-1], "(UID X-GM-MSGID FLAGS)")

    def test_incomplete_metadata_is_unavailable_never_zero(self):
        fake = FakeIMAP()
        fake.broken = True
        result = collect("user", "password", imap_factory=lambda *a, **k: fake)
        self.assertEqual(result["status"], "UNAVAILABLE")
        self.assertIsNone(result["total_count"])
        self.assertIsNone(result["unread_count"])
        self.assertEqual(fake.calls[-1], ("LOGOUT",))

    def test_missing_credentials_does_not_connect(self):
        def forbidden(*args, **kwargs):
            self.fail("Should not connect")
        self.assertIsNone(collect("", "", imap_factory=forbidden)["total_count"])

    def test_empty_result_is_verified_zero(self):
        fake = FakeIMAP()
        fake.uid = lambda *args: ("OK", [b""])
        result = collect("user", "password", imap_factory=lambda *a, **k: fake)
        self.assertEqual(result["status"], "CHECKED")
        self.assertEqual(result["total_count"], 0)

    def test_folder_filter_rejects_other_scopes_and_malformed_listing(self):
        self.assertEqual(pdufa_folders([b'(\\HasNoChildren) "/" "INBOX"',
                                       b'(\\HasNoChildren) "/" "PDUFA-other"']), [])
        with self.assertRaises(ValueError):
            pdufa_folders([b"bad list response"])


if __name__ == "__main__":
    unittest.main()

import unittest

from doi_request.auth import hash_password, verify_password


class AuthTest(unittest.TestCase):

    def test_hash_password_rejects_empty_password(self):
        with self.assertRaises(ValueError):
            hash_password('')

    def test_hash_password_and_verify_password(self):
        password_hash = hash_password('secret-password')

        self.assertTrue(password_hash.startswith('pbkdf2_sha256$'))
        self.assertTrue(verify_password('secret-password', password_hash))
        self.assertFalse(verify_password('wrong-password', password_hash))

import unittest
from app.core.config import Settings


class ProductionSecurityTests(unittest.TestCase):
    def make_settings(self, **kwargs):
        return Settings(_env_file=None, app_env="production", **kwargs)

    def test_default_jwt_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "JWT"):
            self.make_settings().validate_production()

    def test_short_admin_password_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "bootstrap"):
            self.make_settings(jwt_secret_key="x" * 64, initial_admin_password="short").validate_production()

    def test_credentials_require_encrypted_transports(self):
        with self.assertRaisesRegex(RuntimeError, "HTTPS"):
            self.make_settings(jwt_secret_key="x" * 64, ai_api_key="test", ai_api_base_url="http://example.test").validate_production()
        with self.assertRaisesRegex(RuntimeError, "TLS"):
            self.make_settings(jwt_secret_key="x" * 64, smtp_password="test", smtp_security="none").validate_production()

    def test_strong_production_settings_are_accepted(self):
        self.make_settings(jwt_secret_key="x" * 64, initial_admin_password="x" * 24,
                           smtp_password="test", smtp_security="ssl").validate_production()

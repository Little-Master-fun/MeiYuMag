"""Run the additive migration on an isolated existing schema, including rollback."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


class SecondaryMigrationTests(unittest.TestCase):
    def test_upgrade_preserves_existing_requests_and_downgrade_returns_pending_work(self):
        path = Path(__file__).parents[1] / 'alembic/versions/86f21d7c0a34_secondary_review.py'
        spec = importlib.util.spec_from_file_location('secondary_migration', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        engine = sa.create_engine('sqlite:///:memory:')
        with engine.begin() as db:
            db.execute(sa.text('CREATE TABLE users (id INTEGER PRIMARY KEY, role VARCHAR(32))'))
            db.execute(sa.text('CREATE TABLE applications (id INTEGER PRIMARY KEY, status VARCHAR(64))'))
            db.execute(sa.text("INSERT INTO users VALUES (1, 'admin'), (2, 'user')"))
            db.execute(sa.text("INSERT INTO applications VALUES (1, 'pending_admin_submit')"))
            operations = Operations(MigrationContext.configure(db))
            with patch.object(module, 'op', operations):
                module.upgrade()
                self.assertEqual(db.execute(sa.text('SELECT status, secondary_reviewer_id FROM applications')).one(), ('pending_admin_submit', None))
                self.assertTrue(sa.inspect(db).get_foreign_keys('applications'))
                db.execute(sa.text("UPDATE users SET role='secondary_admin' WHERE id=2"))
                db.execute(sa.text("UPDATE applications SET status='pending_secondary_signature', secondary_reviewer_id=2"))
                module.downgrade()
                self.assertEqual(db.execute(sa.text('SELECT status FROM applications')).scalar(), 'pending_admin_submit')
                self.assertEqual(db.execute(sa.text('SELECT role FROM users WHERE id=2')).scalar(), 'user')
                self.assertNotIn('secondary_reviewer_id', [column['name'] for column in sa.inspect(db).get_columns('applications')])
        engine.dispose()

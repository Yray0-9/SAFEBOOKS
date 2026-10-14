"""Migration checks use only the isolated test database and synthetic records."""
from django.db import IntegrityError, connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.recorder import MigrationRecorder
from django.test import TransactionTestCase


class AccountIdentifierMigrationTests(TransactionTestCase):
    migrate_from = [("safebooks", "0033_account_session_version")]
    migrate_to = [("safebooks", "0034_account_case_insensitive_unique")]
    constraint_names = {"bk_email_ci_unique", "bk_username_ci_unique", "admin_email_ci_unique"}

    def setUp(self):
        super().setUp()
        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_from)
        self.apps = executor.loader.project_state(self.migrate_from).apps
        self.duplicates = []
        self.admin_model = self.apps.get_model("safebooks", "AdminAccount")
        self.owner_model = self.apps.get_model("safebooks", "BookkeeperAccount")
        self.admin = self.admin_model.objects.create(full_name="Synthetic Admin", email="Admin@Example.test", password_hash="synthetic-unused", session_version=7)
        self.owner = self.owner_model.objects.create(full_name="Synthetic Owner", username="MixedOwner", email="Owner@Example.test", password_hash="synthetic-unused", session_version=11)

    def tearDown(self):
        try:
            # Remove only this test's duplicate fixtures so the latest schema can be restored.
            for model, pk in self.duplicates:
                model.objects.filter(pk=pk).delete()
            MigrationExecutor(connection).migrate(self.migrate_to)
        finally:
            super().tearDown()

    def snapshot(self):
        return {
            model.__name__: list(model.objects.order_by("pk").values())
            for model in self.apps.get_app_config("safebooks").get_models()
        }

    def test_upgrade_reverse_and_reapply_preserve_all_existing_values_and_relationships(self):
        client_model = self.apps.get_model("safebooks", "Client")
        client = client_model.objects.create(bookkeeper=self.owner, client_name="Synthetic Client", tin_number="123456789000", location="Test City", email_password="synthetic-unused")
        period_model = self.apps.get_model("safebooks", "Period")
        period = period_model.objects.create(client=client, year=2026, month=4)
        record_model = self.apps.get_model("safebooks", "FinancialRecord")
        record = record_model.objects.create(bookkeeper=self.owner, client=client, period=period, entry_date="2026-04-15", total_amount="100.00")
        self.apps.get_model("safebooks", "FinancialRecordLine").objects.create(record=record, type_code="Sales", description="Synthetic", amount="100.00")
        before = self.snapshot()
        for target in (self.migrate_to, self.migrate_from, self.migrate_to):
            MigrationExecutor(connection).migrate(target)
            self.assertEqual(self.snapshot(), before)
        with connection.cursor() as cursor:
            actual = set()
            for table in ("bookkeeper_accounts", "admin_accounts"):
                actual.update(name for name, info in connection.introspection.get_constraints(cursor, table).items() if info["unique"])
        self.assertTrue(self.constraint_names.issubset(actual))

    def assert_existing_duplicates_block_migration_without_rewriting_data(self, model, **values):
        duplicate = model.objects.create(full_name="Synthetic Duplicate", password_hash="synthetic-unused", **values)
        self.duplicates.append((model, duplicate.pk))
        before = self.snapshot()
        with self.assertRaises(IntegrityError):
            MigrationExecutor(connection).migrate(self.migrate_to)
        self.assertEqual(self.snapshot(), before)
        self.assertFalse(MigrationRecorder(connection).migration_qs.filter(app="safebooks", name=self.migrate_to[0][1]).exists())
        with connection.cursor() as cursor:
            for table in ("bookkeeper_accounts", "admin_accounts"):
                constraints = connection.introspection.get_constraints(cursor, table)
                self.assertFalse(self.constraint_names.intersection(constraints))

    def test_existing_case_variant_bookkeeper_emails_block_upgrade_safely(self):
        self.assert_existing_duplicates_block_migration_without_rewriting_data(self.owner_model, email=self.owner.email.lower(), username="DifferentOwner")

    def test_existing_case_variant_usernames_block_upgrade_safely(self):
        self.assert_existing_duplicates_block_migration_without_rewriting_data(self.owner_model, email="different@example.test", username=self.owner.username.lower())

    def test_existing_case_variant_admin_emails_block_upgrade_safely(self):
        self.assert_existing_duplicates_block_migration_without_rewriting_data(self.admin_model, email=self.admin.email.lower())

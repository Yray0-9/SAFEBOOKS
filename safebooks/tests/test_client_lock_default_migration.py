"""The opt-in default never changes existing account preferences."""
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class ClientLockDefaultMigrationTests(TransactionTestCase):
    before = [("safebooks", "0038_client_tax_registration")]
    after = [("safebooks", "0039_client_details_lock_opt_in")]

    def tearDown(self):
        try:
            MigrationExecutor(connection).migrate(self.after)
        finally:
            super().tearDown()

    def test_forward_reverse_preserve_saved_choices_and_new_default_is_off(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.before)
        model = executor.loader.project_state(self.before).apps.get_model("safebooks", "BookkeeperAccount")
        for enabled in (False, True):
            model.objects.create(full_name="Synthetic Account", username=f"saved_lock_{enabled}",
                email=f"saved-lock-{enabled}@example.test", password_hash="synthetic-unused",
                client_details_password_required=enabled)
        snapshot = list(model.objects.order_by("pk").values())
        for target in (self.after, self.before, self.after):
            executor = MigrationExecutor(connection)
            executor.migrate(target)
            self.assertEqual(list(model.objects.order_by("pk").values()), snapshot)
        new_model = executor.loader.project_state(self.after).apps.get_model("safebooks", "BookkeeperAccount")
        self.assertFalse(new_model._meta.get_field("client_details_password_required").default)
        new = new_model.objects.create(full_name="Synthetic New Account", username="new_lock_default",
            email="new-lock-default@example.test", password_hash="synthetic-unused")
        new.refresh_from_db()
        self.assertFalse(new.client_details_password_required)

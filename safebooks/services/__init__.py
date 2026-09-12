# Service layer package for backend business logic.

from .auth_service import login_user, login_user_or_admin, register_user
from .client_service import (
	create_client_for_bookkeeper,
	delete_client_for_bookkeeper,
	list_clients_for_bookkeeper,
	reopen_client_for_bookkeeper,
	update_client_for_bookkeeper,
)
from .financial_record_service import (
	create_record_for_client_period,
	delete_record_for_client,
	list_financial_clients_for_bookkeeper,
	list_records_for_client_period,
	list_transactions_for_client_range,
	update_record_for_client_period,
)
from .dashboard_service import get_dashboard_summary_for_bookkeeper
from .analytics_service import get_analytics_summary_for_bookkeeper
from .admin_approvals_service import (
	approve_bookkeeper,
	reject_bookkeeper,
	list_admin_approvals,
)
from .admin_bookkeepers_service import (
	list_admin_bookkeepers,
	deactivate_bookkeeper,
	reactivate_bookkeeper,
	delete_bookkeeper_account,
)
from .admin_dashboard_service import get_admin_dashboard_summary
from .security_service import (
	change_bookkeeper_password,
	confirm_client_details_access,
	create_bookkeeper_two_factor_setup,
	disable_bookkeeper_two_factor,
	enable_bookkeeper_two_factor,
	get_bookkeeper_two_factor_status,
	update_client_details_access_preference,
	update_login_alerts_preference,
	verify_bookkeeper_two_factor_login,
)

__all__ = [
	"login_user",
	"login_user_or_admin",
	"register_user",
	"list_clients_for_bookkeeper",
	"create_client_for_bookkeeper",
	"update_client_for_bookkeeper",
	"delete_client_for_bookkeeper",
	"reopen_client_for_bookkeeper",
	"list_financial_clients_for_bookkeeper",
	"list_records_for_client_period",
	"list_transactions_for_client_range",
	"create_record_for_client_period",
	"update_record_for_client_period",
	"delete_record_for_client",
	"get_dashboard_summary_for_bookkeeper",
	"get_analytics_summary_for_bookkeeper",
	"list_admin_approvals",
	"approve_bookkeeper",
	"reject_bookkeeper",
	"list_admin_bookkeepers",
	"deactivate_bookkeeper",
	"reactivate_bookkeeper",
	"delete_bookkeeper_account",
	"get_admin_dashboard_summary",
	"change_bookkeeper_password",
	"update_login_alerts_preference",
	"confirm_client_details_access",
	"update_client_details_access_preference",
	"get_bookkeeper_two_factor_status",
	"create_bookkeeper_two_factor_setup",
	"enable_bookkeeper_two_factor",
	"disable_bookkeeper_two_factor",
	"verify_bookkeeper_two_factor_login",
]

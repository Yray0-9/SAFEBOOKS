"""
Central registry of all database table models used by SafeBooks.

Rule for future phases:
- Keep one table per model file (example: client_model.py, period_model.py)
- Register every new table model here for easy migration preparation and auditing.
"""

from .admin_model import AdminAccount, AdminAuditLog
from .user_model import BookkeeperAccount
from .bookkeeper_proof_model import BookkeeperProof
from .client_model import Client
from .period_model import Period
from .financial_record_model import FinancialRecord
from .financial_record_line_model import FinancialRecordLine
from .workspace_defaults_model import WorkspaceDefaults
from .deactivation_request_model import BookkeeperDeactivationRequest
from .bookkeeper_audit_model import BookkeeperAuditLog

ALL_TABLE_MODELS = (
    AdminAccount,
    AdminAuditLog,
    BookkeeperAccount,
    BookkeeperProof,
    BookkeeperDeactivationRequest,
    BookkeeperAuditLog,
    Client,
    Period,
    FinancialRecord,
    FinancialRecordLine,
    WorkspaceDefaults,
)

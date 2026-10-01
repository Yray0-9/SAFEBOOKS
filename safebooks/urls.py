"""
URL configuration for safebooks project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.staticfiles.storage import staticfiles_storage
from django.urls import path
from django.views.generic import RedirectView

from safebooks import views

urlpatterns = [
    #path('django-admin/', admin.site.urls),
    path(
        'favicon.ico',
        RedirectView.as_view(url=staticfiles_storage.url('images/favicon.ico'), permanent=False),
    ),
    path('', views.home_page_view, name='home'),
    path('login/', views.login_page_view, name='login'),
    path('signup/', views.signup_page_view, name='signup'),
    path('register/', views.signup_page_view, name='register'),
    path('auth/google/start/', views.auth_google_start_view, name='auth_google_start'),
    path('auth/google/callback/', views.auth_google_callback_view, name='auth_google_callback'),
    path('api/auth/login/', views.login_view, name='api_login'),
    path('api/auth/admin-2fa/verify/', views.admin_two_factor_login_verify_view, name='api_admin_two_factor_login_verify'),
    path('api/auth/bookkeeper-2fa/verify/', views.bookkeeper_two_factor_login_verify_view, name='api_bookkeeper_two_factor_login_verify'),
    path('api/auth/register/', views.register_view, name='api_register'),
    path('api/auth/google/complete-signup/', views.google_complete_signup_view, name='api_google_complete_signup'),
    path('api/auth/logout/', views.logout_view, name='api_logout'),
    path('api/auth/email/resend/', views.resend_email_verification_api_view, name='api_resend_verification'),
    path('api/auth/email/verify/', views.verify_email_api_view, name='api_verify_email'),
    path('api/auth/password/forgot/send-code/', views.forgot_password_send_code_api_view, name='api_forgot_password_send_code'),
    path('api/auth/password/forgot/verify-code/', views.forgot_password_verify_code_api_view, name='api_forgot_password_verify_code'),
    path('api/auth/password/forgot/reset/', views.forgot_password_reset_api_view, name='api_forgot_password_reset'),
    path('api/feedback/submit/', views.submit_feedback_api_view, name='api_submit_feedback'),
    path('api/settings/workspace-defaults/', views.workspace_defaults_api_view, name='api_workspace_defaults'),
    path('api/settings/notifications/client-record-emails/', views.settings_client_record_email_notifications_api_view, name='api_settings_client_record_email_notifications'),
    path('api/settings/security/password/', views.security_change_password_api_view, name='api_security_change_password'),
    path('api/settings/security/login-alerts/', views.security_login_alerts_api_view, name='api_security_login_alerts'),
    path('api/settings/security/client-details-access/', views.security_client_details_access_preference_api_view, name='api_security_client_details_access_preference'),
    path('api/settings/security/two-factor/setup/', views.bookkeeper_two_factor_setup_api_view, name='api_bookkeeper_two_factor_setup'),
    path('api/settings/security/two-factor/confirm/', views.bookkeeper_two_factor_confirm_api_view, name='api_bookkeeper_two_factor_confirm'),
    path('api/settings/security/two-factor/disable/', views.bookkeeper_two_factor_disable_api_view, name='api_bookkeeper_two_factor_disable'),
    path('api/settings/account/deactivation-request/', views.settings_deactivation_request_api_view, name='api_settings_deactivation_request'),
    path('api/security/client-details-access/confirm/', views.security_client_details_access_confirm_api_view, name='api_security_client_details_access_confirm'),
    path('api/profile/', views.profile_api_view, name='api_profile'),
    path('api/audit-log/', views.bookkeeper_audit_log_api_view, name='api_bookkeeper_audit_log'),
    path('api/clients/', views.clients_api_view, name='api_clients'),
    path('api/clients/<int:client_id>/', views.client_detail_api_view, name='api_client_detail'),
    path('api/clients/<int:client_id>/reopen/', views.client_reopen_api_view, name='api_client_reopen'),
    path('api/dashboard/summary/', views.dashboard_summary_api_view, name='api_dashboard_summary'),
    path('api/analytics/summary/', views.analytics_summary_api_view, name='api_analytics_summary'),
    path('api/reports/print-layout/', views.reports_print_layout_api_view, name='api_reports_print_layout'),
    path('api/financial-records/clients/', views.financial_record_clients_api_view, name='api_financial_record_clients'),
    path('api/financial-records/client/<int:client_id>/records/', views.financial_records_api_view, name='api_financial_records'),
    path('api/financial-records/client/<int:client_id>/records/last/', views.financial_records_last_entry_api_view, name='api_financial_records_last_entry'),
    path('api/financial-records/client/<int:client_id>/records/<int:record_id>/', views.financial_record_detail_api_view, name='api_financial_record_detail'),
    path('api/admin/approvals/', views.admin_approvals_api_view, name='api_admin_approvals'),
    path('api/admin/approvals/<int:bookkeeper_id>/approve/', views.admin_approvals_approve_api_view, name='api_admin_approvals_approve'),
    path('api/admin/approvals/<int:bookkeeper_id>/reject/', views.admin_approvals_reject_api_view, name='api_admin_approvals_reject'),
    path('api/admin/approvals/<int:bookkeeper_id>/retry-email/', views.admin_approvals_retry_email_api_view, name='api_admin_approvals_retry_email'),
    path('api/admin/dashboard/summary/', views.admin_dashboard_summary_api_view, name='api_admin_dashboard_summary'),
    path('api/admin/bookkeepers/', views.admin_bookkeepers_api_view, name='api_admin_bookkeepers'),
    path('api/admin/bookkeepers/<int:bookkeeper_id>/deactivate/', views.admin_bookkeepers_deactivate_api_view, name='api_admin_bookkeepers_deactivate'),
    path('api/admin/bookkeepers/deactivation-requests/<int:request_id>/decline/', views.admin_bookkeepers_deactivation_request_decline_api_view, name='api_admin_bookkeepers_deactivation_request_decline'),
    path('api/admin/bookkeepers/<int:bookkeeper_id>/reactivate/', views.admin_bookkeepers_reactivate_api_view, name='api_admin_bookkeepers_reactivate'),
    path('api/admin/bookkeepers/<int:bookkeeper_id>/delete/', views.admin_bookkeepers_delete_api_view, name='api_admin_bookkeepers_delete'),
    path('api/admin/audit-log/', views.admin_audit_log_api_view, name='api_admin_audit_log'),
    path('api/admin/profile/', views.admin_profile_api_view, name='api_admin_profile'),
    path('api/admin/security/password/', views.admin_security_change_password_api_view, name='api_admin_security_password'),
    path('api/admin/security/2fa/setup/', views.admin_two_factor_setup_api_view, name='api_admin_two_factor_setup'),
    path('api/admin/security/2fa/confirm/', views.admin_two_factor_confirm_api_view, name='api_admin_two_factor_confirm'),
    path('api/admin/security/2fa/disable/', views.admin_two_factor_disable_api_view, name='api_admin_two_factor_disable'),
    path('api/admin/security/2fa/recovery-codes/', views.admin_two_factor_recovery_codes_api_view, name='api_admin_two_factor_recovery_codes'),
    path('admin/', views.admin_dashboard_page_view, name='admin_root'),
    path('admin/dashboard/', views.admin_dashboard_page_view, name='admin_dashboard'),
    path('admin/bookkeepers/', views.admin_bookkeepers_page_view, name='admin_bookkeepers'),
    path('admin/approvals/', views.admin_approvals_page_view, name='admin_approvals'),
    path('admin/audit-log/', views.admin_audit_log_page_view, name='admin_audit_log'),
    path('admin/system-settings/', views.admin_system_settings_page_view, name='admin_system_settings'),
    path('admin/profile/', views.admin_profile_page_view, name='admin_profile'),
    path('dashboard/', views.dashboard_page_view, name='dashboard'),
    path('clients/', views.clients_page_view, name='clients'),
    path('clients/<int:client_id>/', views.client_details_page_view, name='client_details'),
    path('financial-records/', views.financial_records_page_view, name='financial_records'),
    path('financial-records/client/', views.financial_records_client_page_view, name='financial_records_client'),
    path('reports/', views.reports_page_view, name='reports'),
    path('verify-email/', views.verify_email_page_view, name='verify_email'),
    path('pending-approval/', views.pending_approval_page_view, name='pending_approval'),
    path('settings/', views.settings_page_view, name='settings'),
    path('profile/', views.profile_page_view, name='profile'),
    path('audit-log/', views.bookkeeper_audit_log_page_view, name='bookkeeper_audit_log'),
]

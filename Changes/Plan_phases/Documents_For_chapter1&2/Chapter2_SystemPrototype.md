# System Prototype

The system prototype presents the visual design and user interface of the SafeBooks platform for both the Bookkeeper and System Administrator. It illustrates the system screens, navigation flow, and major functionalities developed based on the identified requirements of the study.

## 2.1 Bookkeeper Interface System Prototype

The following figures illustrate the visual designs and user interfaces developed for the Bookkeeper role in the SafeBooks platform, depicting the major functional screens and analytical dashboards utilized in daily accounting tasks:

### 2.1.1 Bookkeeper Dashboard
**Figure 10: Bookkeeper Dashboard**

Figure 10 shows the Bookkeeper Dashboard representing the central operational hub of the SafeBooks platform. The dashboard aggregates core accounting and compliance metrics at a single glance, displaying real-time counters for total active clients, monthly transaction entry counts, pending compliance deadlines, and newly registered clients in onboarding phases. It also features a real-time list of recent client activities, showing TIN numbers and filing statuses, alongside a categorical breakdown of client remarks and compliance status overviews.

---

### 2.1.2 Active Clients Directory Interface
**Figure 11: Active Clients Directory**

Figure 11 displays the Active Clients Directory interface, which serves as the centralized repository for client profiles under the bookkeeper's jurisdiction. This dashboard enables the bookkeeper to register new clients, browse active client credentials, locate TIN numbers, assign business locations, and check trade names. It partitions the active directory from deactivated or closed accounts to ensure data hygiene and simple list navigation.

---

### 2.1.3 Analytics and Financial Insights
**Figure 12: Analytics and Financial Insights**

Figure 12 illustrates the Analytics and Financial Insights page of the SafeBooks platform. This screen processes historical bookkeeping logs to render key financial metrics such as total cumulative sales, business expenses, BIR-standard tax aggregates, and net value. It also features a mathematical next-period forecasting trend line chart spanning the latest 6 months and highlights automated client remarks summaries (Active, Separated, New, Closed) computed directly from filing patterns.

---

### 2.1.4 Financial Records Client Directory
**Figure 13: Financial Records Directory**

Figure 13 showcases the Financial Records Client Directory page. This workspace allows bookkeepers to manage monthly ledger files by selecting individual clients. The page displays the last recorded activity timestamps and features real-time countdown alerts (such as the orange '5d left' badge) to flag clients who are close to their filing deadlines, enabling bookkeepers to prioritize their compliance workflow efficiently.

---

### 2.1.5 Reports Builder Interface
**Figure 14: Reports Builder**

Figure 14 displays the Reports Builder interface, which provides bookkeepers with powerful filtering and generation capabilities. The interface enables the selection of report types (such as financial summaries or remarks reports), date scopes, and specific client queries. Bookkeepers can instantly preview, print, or export generated sheets, and quickly access recent reports from their current session for dynamic updates.
---

### 2.1.6 Bookkeeper Workspace Settings
**Figure 15: Bookkeeper Settings Interface**

Figure 15 shows the Settings page of the Bookkeeper workspace, which serves as the control center for account and workspace configuration. The settings panel allows the bookkeeper to define workspace defaults (such as default client scope, report types, report date ranges, and PHP currency formats) to expedite recurring ledger generations. It also features an appearance theme selector allowing the bookkeeper to switch between Light and Dark interface modes to optimize visual comfort across different operating environments.

---

### 2.1.7 Bookkeeper Profile Management
**Figure 16: Bookkeeper Profile Interface**

Figure 16 displays the Profile Management screen, which represents the bookkeeper's primary identity and verification console. The profile interface features a progress tracker displaying profile completion percentage (such as the 100% completed badge), alongside actions to edit profile data, update email credentials, change password, and request account deactivation under a planned danger zone. It also presents a preferences snapshot displaying active system modes (such as Light Theme and active alert configurations).

---

## 2.2 System Administrator Interface System Prototype

The following figures illustrate the visual designs and user interfaces developed for the Administrator role in the SafeBooks platform, depicting the supervisor's system-level home console, approvals tracking dashboard, and active user list managers:

### 2.2.1 Administrator Overview Dashboard
**Figure 17: Administrator Home Console**

Figure 17 displays the Administrator Home Console, representing the central supervisory overview dashboard of the SafeBooks platform. The console displays aggregate indicators for total bookkeeper directories, pending approvals, active accounts, and bookkeepers with high client loads. It also features a real-time bookkeeper load snapshot displaying client list sizes per operator, an approval readiness chart displaying pending registration durations, and quick actions to navigate directly to approvals lists or user directories.

---

### 2.2.2 Administrator Bookkeeper Directory
**Figure 18: Administrator Bookkeeper Directory**

Figure 18 illustrates the Administrator Bookkeeper Directory interface, which provides a comprehensive, searchable list of all registered bookkeepers in the system. The directory panel allows administrators to search operators by name or email, apply filters by registration status (Approved, Deactivated, Inactive) or workload sizes (0-15 or 16+ clients), and perform administrative actions such as deactivating or deleting user records. It also provides graphical sidebars summarizing overall approval ratios and operators' client distributions.

---

### 2.2.3 Administrator Approvals Queue
**Figure 19: Administrator Approvals Interface**

Figure 19 displays the Administrator Approvals interface, which serves as the verification gatekeeper for newly registered bookkeeper accounts. The approvals console features a main request queue showcasing bookkeeper names, email addresses, request timestamps, and status indicators (Pending or Approved), with dedicated action keys to instantly approve, reject, or view detailed profiles. It also provides a sidebar summarizing overall approval metrics (Pending, Approved, Rejected, and daily outcomes) alongside dedicated review note fields for recording administrative audit remarks.

---

### 2.2.4 Administrator System Settings
**Figure 20: Administrator System Settings Interface**

Figure 20 illustrates the System Settings interface, which provides administrators with centralized controls to manage global application policies, SLA schedules, and capacity configurations. The settings console contains sections to define the default approval workflow (manual or auto-approvals modes), SLA escalation limits (e.g. 24 hours SLA targets with escalation reminders after 4 days), mandatory rejection reason validations, and bookkeeper capacity alerts (e.g. 90-day inactivity flag windows and 150-client workload thresholds).

---

### 2.2.5 Administrator Profile Management
**Figure 21: Administrator Profile Interface**

Figure 21 displays the Administrator Profile interface, which enables supervisors to manage their account identity, credentials, and system visibility parameters. The console features identity detail editors, dynamic activity snapshots displaying logged onboarding actions, and an active security preferences panel for configuring session timeouts (e.g. 30-minute thresholds), multi-factor authentication, and re-authentication rules. It also includes a trusted devices list allowing the administrator to inspect active login sessions (e.g. Chrome or Edge on Windows) and instantly revoke unauthorized access.

---

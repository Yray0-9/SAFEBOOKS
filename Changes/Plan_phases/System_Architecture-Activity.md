# SafeBooks — System Architecture Activity

## Diagram 1: Logical View

### What Is a Logical View?

A Logical View shows **how the software system is organized internally** — its major components (modules), what each one is responsible for, and how they depend on each other. Think of it as an X-ray of the system's brain: not what it looks like from outside, but how its internal parts are structured and connected.

It answers the question: **"What are the building blocks of this system and how do they relate?"**

---

### Diagram Type to Use

**Layered Component Diagram** — Draw the system as horizontal layers stacked on top of each other (like a cake). Each layer contains named boxes (components). Arrows point **downward** from a component to the layer it depends on.

---

### Diagram Layout Guide

Draw **5 horizontal layers** stacked vertically. The topmost layer is what the user sees (browser), and the bottom layer is the database. Here is the exact content for each layer:

---

#### LAYER 1 (Top) — Presentation Layer

> **Label this layer:** `Presentation Layer (Client-Side)`

This layer represents everything that runs **inside the user's web browser**.

Draw **3 boxes** inside this layer:

| Box Name | Description (for your reference, don't write this on diagram) |
|---|---|
| **HTML Templates** | The pages rendered by Django and displayed in the browser |
| **CSS Stylesheets** | All visual styling — layout, colors, dark mode, responsive design |
| **JavaScript Modules** | Client-side interactivity — form handling, API calls, charts, toggles |

---

#### LAYER 2 — Application Layer (Bookkeeper Side)

> **Label this layer:** `Bookkeeper Application Module`

This layer shows all the features/pages accessible to the **Bookkeeper** user role.

Draw **7 boxes** inside this layer:

| Box Name | What It Represents |
|---|---|
| **Dashboard** | Overview with analytics summary, deadline tracking, WMA forecasts |
| **Client Management** | Add, view, edit, and manage client profiles and details |
| **Financial Records** | Record financial entries, manage transaction lines per client/period |
| **Reports & Printing** | Generate, filter, preview, and print/export client financial reports |
| **Analytics & Forecasting** | Charts, trend analysis, and Weighted Moving Average (WMA) forecasting |
| **Bookkeeper Profile** | View/edit personal profile, change password, manage 2FA |
| **Activity Log** | View personal audit trail of actions performed in the system |

---

#### LAYER 3 — Application Layer (Admin Side)

> **Label this layer:** `Admin Application Module`

This layer shows all the features/pages accessible to the **System Administrator** user role.

Draw **6 boxes** inside this layer:

| Box Name | What It Represents |
|---|---|
| **Admin Dashboard** | System-wide metrics — total bookkeepers, clients, records, pending actions |
| **Bookkeeper Management** | View, filter, search all bookkeeper accounts and their details |
| **Registration Approvals** | Review, approve, or reject new bookkeeper registration requests |
| **System Settings** | Configure governance, security policies, notifications, and maintenance |
| **Admin Profile & 2FA** | Admin profile management, password change, two-factor authentication |
| **Admin Audit Log** | Review system-wide audit records of all administrative actions |

---

#### LAYER 4 — Shared Services Layer

> **Label this layer:** `Shared Services Layer (Backend Logic)`

This is the **core engine** of the system — the reusable backend services that both the Bookkeeper and Admin modules depend on. This layer sits between the application modules above and the database below.

Draw **8 boxes** inside this layer:

| Box Name | What It Does |
|---|---|
| **Authentication Service** | Handles login, logout, signup, email verification, session management |
| **Two-Factor Auth (TOTP)** | TOTP-based authenticator setup, verification, recovery code management |
| **Role-Based Access Control** | Middleware that enforces Bookkeeper vs. Admin permissions on every request |
| **Analytics & Forecasting Engine** | Calculates summary statistics, WMA forecasts, and trend data |
| **Financial Record Service** | Business logic for creating, validating, updating financial records |
| **Audit Logging Service** | Records all user and admin actions into traceable audit logs |
| **Email Notification Service** | Sends approval, rejection, and security alert emails via SMTP |
| **Input Validation** | Server-side password strength, data format, and business rule validation |

---

#### LAYER 5 (Bottom) — Data Layer

> **Label this layer:** `Data Layer (Persistence)`

This is the database. Draw **2 sections** inside this layer:

| Section Name | Contents |
|---|---|
| **Data Models (Django ORM)** | BookkeepersAccount, AdminAccount, Client, FinancialRecord, TransactionDetail, Period, WorkspaceDefaults, BookkeeperAuditLog, AdminAuditLog, BookkeeperDeactivationRequest |
| **Database Engine** | SQLite (local development) / PostgreSQL (production deployment) |

---

### How to Draw the Arrows (Dependencies)

Arrows represent **"depends on"** or **"uses"** relationships. Draw them pointing **downward** from the component that depends on another.

| From (Source) | To (Target) | Meaning |
|---|---|---|
| Presentation Layer | Bookkeeper Module | Browser renders pages served by the Bookkeeper module |
| Presentation Layer | Admin Module | Browser renders pages served by the Admin module |
| Bookkeeper Module (all boxes) | Shared Services Layer | Bookkeeper features use shared backend services |
| Admin Module (all boxes) | Shared Services Layer | Admin features use shared backend services |
| Shared Services Layer (all boxes) | Data Layer | All services read from and write to the database |
| Email Notification Service | External: Gmail SMTP | Sends emails through an external mail server (draw this as a small cloud or external box outside the layers) |

---

### Complete Visual Blueprint

Here is the exact structure you should draw, top to bottom:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER (Client-Side)                 │
│                                                                     │
│   ┌─────────────────┐  ┌─────────────────┐  ┌────────────────────┐ │
│   │  HTML Templates  │  │ CSS Stylesheets  │  │ JavaScript Modules │ │
│   └─────────────────┘  └─────────────────┘  └────────────────────┘ │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ renders pages from
              ┌────────────────┴────────────────┐
              ▼                                  ▼
┌──────────────────────────────┐ ┌──────────────────────────────────┐
│ BOOKKEEPER APPLICATION       │ │ ADMIN APPLICATION                │
│ MODULE                       │ │ MODULE                           │
│                              │ │                                  │
│ ┌──────────┐ ┌─────────────┐│ │ ┌───────────────┐ ┌────────────┐│
│ │Dashboard │ │Client Mgmt  ││ │ │Admin Dashboard│ │Bookkeeper  ││
│ └──────────┘ └─────────────┘│ │ └───────────────┘ │Management  ││
│ ┌──────────┐ ┌─────────────┐│ │ ┌───────────────┐ └────────────┘│
│ │Financial │ │Reports &    ││ │ │Registration   │ ┌────────────┐│
│ │Records   │ │Printing     ││ │ │Approvals      │ │System      ││
│ └──────────┘ └─────────────┘│ │ └───────────────┘ │Settings    ││
│ ┌──────────┐ ┌─────────────┐│ │ ┌───────────────┐ └────────────┘│
│ │Analytics │ │Bookkeeper   ││ │ │Admin Profile  │ ┌────────────┐│
│ │&Forecast │ │Profile      ││ │ │& 2FA          │ │Admin Audit ││
│ └──────────┘ └─────────────┘│ │ └───────────────┘ │Log         ││
│ ┌──────────┐                │ │                    └────────────┘│
│ │Activity  │                │ │                                  │
│ │Log       │                │ │                                  │
│ └──────────┘                │ │                                  │
└──────────────┬───────────────┘ └──────────────┬───────────────────┘
               │ uses                            │ uses
               └───────────────┬─────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  SHARED SERVICES LAYER (Backend Logic)              │
│                                                                     │
│  ┌──────────────────┐  ┌───────────────────┐  ┌──────────────────┐ │
│  │ Authentication   │  │ Two-Factor Auth   │  │ Role-Based       │ │
│  │ Service          │  │ (TOTP)            │  │ Access Control   │ │
│  └──────────────────┘  └───────────────────┘  └──────────────────┘ │
│  ┌──────────────────┐  ┌───────────────────┐  ┌──────────────────┐ │
│  │ Analytics &      │  │ Financial Record  │  │ Audit Logging    │ │
│  │ Forecasting      │  │ Service           │  │ Service          │ │
│  └──────────────────┘  └───────────────────┘  └──────────────────┘ │
│  ┌──────────────────┐  ┌───────────────────┐                       │
│  │ Email            │  │ Input             │          ┌──────────┐ │
│  │ Notification     │──┼──▶ Gmail SMTP     │          │Validation│ │
│  │ Service          │  │ (External)        │          └──────────┘ │
│  └──────────────────┘  └───────────────────┘                       │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ reads / writes
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      DATA LAYER (Persistence)                       │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    Data Models (Django ORM)                    │  │
│  │                                                               │  │
│  │  BookkeepersAccount  │  AdminAccount   │  Client              │  │
│  │  FinancialRecord     │  TransactionDetail │ Period             │  │
│  │  WorkspaceDefaults   │  BookkeeperAuditLog │ AdminAuditLog    │  │
│  │  BookkeeperDeactivationRequest                                │  │
│  └───────────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │           SQLite (Development) / PostgreSQL (Production)      │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

### Drawing Tips

1. **Title:** Place at the top or bottom: **"Figure X: SafeBooks Logical View Diagram"**
2. **Layer labels:** Write each layer name on the left side or as a header bar across the top of each horizontal band
3. **Boxes:** Each component is a simple rectangle with its name centered inside
4. **Arrows:** Use solid arrows pointing downward. Label them with short phrases like "uses," "depends on," or "reads/writes"
5. **Colors (optional but recommended):**
   - Presentation Layer → Light blue
   - Bookkeeper Module → Light green
   - Admin Module → Light orange
   - Shared Services → Light purple/lavender
   - Data Layer → Light gray
6. **Gmail SMTP:** Draw this as a small box or cloud shape **outside** the main layers, connected to the Email Notification Service with a dashed arrow labeled "sends via SMTP"
7. **Keep it clean:** Don't try to draw every single arrow from every box — use one combined arrow from each module layer down to the Shared Services layer, and one from Shared Services down to Data Layer

---

### How This Differs From Your Existing Diagrams

| Your Existing Diagram | This Logical View |
|---|---|
| **ERD (Figure 10)** — shows database table relationships | Shows the **entire software structure** from browser to database, with ERD entities as just one piece at the bottom |
| **DFD (Figure 8 & 9)** — shows data flowing between processes | Shows **component organization and dependencies**, not data flow |
| **System Architecture (Figure 5)** — shows physical deployment | Shows **logical software modules**, not servers or infrastructure |

---

*Next: Once you complete this Logical View diagram and are satisfied with the result, we will move to Diagram 2 (Runtime View).*

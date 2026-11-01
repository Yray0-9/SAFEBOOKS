# Bookkeeper proof submission and review

Applicants verify their email, then use the existing Pending Approval page to submit one Business Permit, TESDA Certificate, or Other document. Other requires a short document name. Accepted files are validated JPG/PNG images or readable PDFs up to 5 MB; PDFs permit 1–20 pages without passwords or interactive content. The document remains evidence for manual review, not automatic proof of professional qualifications. No PRC credential is mandatory for every bookkeeper.

## Storage and access

`BookkeeperProof` stores one current document per account in the database. There are no public media files or public download URLs. Queue/status queries fetch metadata without loading binary contents. Only the owning authenticated bookkeeper or an authenticated administrator can download a document. Responses are attachments with no-store, nosniff, and sandbox headers.

Database backups now contain private applicant documents. Keep them private and outside Git, as with existing account and financial data. Replacing proof replaces the current binary under the account lock, with a new revision and a submission audit entry. The replaced binary is not kept as an archive; its revision/hash remains in audit history. Account deletion cascades to its proof. Existing approved accounts keep their access without requiring a retrospective upload.

## Approval

The admin downloads the current proof in Approvals, reviews it, then explicitly confirms review in the approval dialog. A server-side download receipt is scoped to that admin's authenticated session and expires after 15 minutes. Approval requires verified email and the same current document revision. Replacement and approval share the account lock, so an outdated review cannot approve a replacement. The approval audit records the reviewed revision/hash atomically with the decision. Existing rejection and post-commit decision email behavior remain unchanged. Rejected accounts retain the existing sign-in restriction; this change does not introduce an appeal/resubmission workflow for them.

Failed submissions retain the draft. Unknown outcomes require reloading to check the saved status; neither the browser nor server automatically repeats the write. No document is labelled Submitted until the server confirms saved metadata.

## API changes

| Endpoint | Access and behavior |
| --- | --- |
| `POST /api/verification/proof/` | Verified pending applicant; multipart `document`, `document_type`, `document_name`, and current `revision` (empty for first submission). |
| `GET /api/verification/proof/<revision>/` | Owning authenticated bookkeeper only. |
| `GET /api/admin/approvals/<bookkeeper_id>/proof/<revision>/` | Authenticated admin; protected download and session-scoped review receipt. |
| Existing approvals list | Adds nullable `proof` metadata to each row; no document bytes or storage paths. |
| Existing approve endpoint | Requires `proof_revision` and boolean `proof_reviewed`, plus the server-side download receipt. Older clients cannot bypass the guard. |

## Installation

Install the updated `requirements.txt` (Pillow and pypdf validate document contents), then run `python manage.py migrate` before restarting the application. Migration `0040_bookkeeper_verification_proof` adds a new table only. It does not rewrite existing accounts, preferences, clients, financial records, or forecasting inputs. No external storage credentials or public media configuration are needed.

## Implementation files

- `safebooks/models/bookkeeper_proof_model.py`, model exports/registry, and migration `0040`.
- `safebooks/validators/bookkeeper_proof_validator.py` and `safebooks/services/bookkeeper_proof_service.py`.
- `safebooks/views.py`, `safebooks/urls.py`, and `safebooks/services/admin_approvals_service.py`.
- `templates/authentication/pending_approval.html`, `templates/admin_panel/approvals.html`, and their existing/new browser scripts and proof-panel CSS.
- Proof API/concurrency tests, approval/auth regressions, and JavaScript submission tests.

# How SafeBooks Was Deployed for Usability Testing

Recorded: October 19, 2026

Live website: [SafeBooks usability site](https://safebooks-usability.onrender.com)

This is a recap of our working deployment, not a list of commands to rerun. It contains no passwords, keys, or private connection strings.

## 1. What each service does

| Service | Its job in SafeBooks |
| --- | --- |
| GitHub | Stores the application code and the `usability-readiness` branch connected to Render. |
| Render | Builds and runs the Django website and provides its public HTTPS address. |
| Neon PostgreSQL | Permanently stores hosted accounts, clients, financial records, and database-backed sessions. |
| Upstash Redis | Shares temporary authentication state and login-attempt counters between application processes. It is not the financial database. |
| Brevo | Sends transactional emails, including verification codes, password-reset codes, and feedback messages. |

We selected Singapore for the Neon and Redis services to keep them geographically close to the planned hosting region.

## 2. How we put it together

1. **Prepared and tested the application.** We addressed deployment-readiness findings, including authentication, ownership checks, validation, financial-write reliability, and workload limits. Isolated tests used synthetic data rather than changing the normal database.

2. **Published the deployment branch.** We pushed `usability-readiness` to GitHub and selected that branch in Render. Render therefore deploys this branch, not automatically `main`.

3. **Configured production separately from localhost.** Render uses `DJANGO_SETTINGS_MODULE=safebooks.settings_production`. This profile does not load the local `.env`; database credentials, Redis credentials, the application secret key, and email settings are supplied through Render's environment variables.

4. **Connected the services.** Neon used its direct PostgreSQL hostname, role, password, port `5432`, and SSL mode `require`. Upstash used a writable TLS Redis URL beginning with `rediss://`. Brevo used `smtp-relay.brevo.com`, port `2525`, STARTTLS, an active SMTP key, and a verified sender.

5. **Initialized the fresh Neon database.** After confirming it was empty, we applied Django migrations and created the first administrator. We verified that the latest SafeBooks migration, `0034`, was recorded and that one administrator existed. Local test records were not copied into Neon.

6. **Built and started the website.** Render used Python `3.14.8`, installed the pinned dependencies in `requirements.txt`, collected static files, and ran production checks. Gunicorn runs Django using `gunicorn.conf.py`; WhiteNoise serves collected CSS, JavaScript, and images. We initially configured one worker and two threads.

7. **Checked the live workflows.** You confirmed administrator login, tester registration and approval, workspace access, and successful receipt of a feedback test email.

## 3. Important problems we resolved

- **A secret blocked the GitHub push:** the exposed SMTP key was deactivated and replaced. With your approval, the two unpublished commits were cleaned while preserving local files. Removing a secret only from the newest file does not remove it from earlier commits.
- **The Neon project name was not the database name:** the project was `safebooksdb`, but the actual database selected in Connect was `neondb`.
- **Redis was copied as a terminal command:** Render needed only the complete `rediss://...` URL—not `redis-cli --tls -u ...`, an HTTPS REST endpoint, or masked asterisks.
- **Administrator creation initially failed after migrations:** we checked the existing database state and created only the missing administrator instead of deleting tables or repeating initialization.
- **Send Feedback was hidden online:** production needed `SAFEBOOKS_FEEDBACK_ENABLED=1` and `SAFEBOOKS_FEEDBACK_RECIPIENT_EMAIL` set to your receiving inbox. The recipient is different from the Brevo SMTP login. After redeployment, you received the test message.

## 4. How future updates reach the live site

Your selected Render setting is **Auto-Deploy: On Commit**. After changes are tested, committed, and pushed to GitHub's `usability-readiness` branch, Render starts a new build and deployment. Wait for **Live**, then check the affected feature online. Saving files or committing without pushing does not update the website.

Normal redeployment keeps the existing Neon database. However, our build/start commands do **not** automatically apply database migrations. Model changes require a separately planned migration against the hosted database; do not rerun first-time initialization.

Keep secrets and database exports out of Git, use fictitious client data during testing, and keep development data separate from hosted data. A working deployment confirms the application can run online; hosted capacity testing and backup/restore verification are separate checks, not guarantees provided by a successful build.

Set up this app on Neon.

1. `npm i -g neon@latest`. If that fails, use `npx neon@latest` in place of `neon`.
   If a neon command opens a browser sign-in, tell me to finish it there. If that times out or fails, ask me to run `neon login`, then retry.
2. In the project root:
   neon init -y --org-id org-lucky-pine-62657669 --project-id wandering-haze-24749377 --branch production --services postgres
3. `neon deploy`. It provisions the services in neon.ts and pulls their env vars into `.env.local` (or `.env` if it exists).
4. Wire each service into the app's code using those env vars. Consult the installed Neon agent skills for best practices, e.g., what database driver to use given the app architecture and hosting runtime.
5. Prove it works: `npm run build` must pass, then start the app, each wired service must be tested to prove it works end to end.
6. Report what changed, the command output that proves step 5, and anything that failed.

Before we proceed with deployment, I want you to perform a very important and thorough review of this entire project.
Your task is to inspect, check, and test everything relevant to determine whether this project is truly ready for deployment. I want you to identify potential problems, vulnerabilities, bugs, and anything else that could cause issues once the system goes live, especially when multiple users are using it simultaneously.
Important: At this stage, your job is strictly limited to checking, testing, analyzing, and reporting. Do not modify, edit, create, delete, refactor, or fix any files or code. Do not make any changes to the project or its configuration. I want you to finish the assessment first and recommend what needs to be done next before any changes are made.
Please conduct a comprehensive review of the following areas:

1. All Project Files and Code — Inspect all relevant files, folders, source code, configurations, dependencies, environment variables, and project structure. Identify errors, missing components, inconsistencies, outdated dependencies, and potential problems. Do not skip files without explaining why they were excluded from the review.
2. All Features and Functionality — Test all features, modules, user flows, business logic, database operations, and interactions between different parts of the system. Verify whether everything works as intended and identify any broken or incomplete functionality.
3. Multi-User Capability — Evaluate how the system behaves when multiple users access and use it simultaneously. Check for potential concurrency issues, race conditions, database conflicts, data leakage between users, performance bottlenecks, resource limitations, and other scalability concerns. Use appropriate tests where possible, without disrupting existing data or services.
4. All APIs and Integrations — Inspect and test all API endpoints, request and response handling, input validation, error responses, authentication requirements, authorization rules, rate limiting, and external integrations. Identify endpoints that are broken, insecure, incomplete, or behaving unexpectedly.
5. Security and Authentication — Thoroughly assess authentication, authorization, session management, access controls, password handling, data protection, exposed secrets, insecure configurations, injection vulnerabilities, and other relevant security risks. Identify weaknesses and explain their potential impact.
6. Database and Data Integrity — Check database schemas, relationships, queries, transactions, migrations, validation, access permissions, and data consistency. Identify potential data loss, corruption, duplication, unauthorized access, or conflicts when multiple users operate on the system.
7. Performance and Stability — Evaluate loading times, resource consumption, inefficient operations, potential memory leaks, bottlenecks, and system behavior under realistic workloads. Determine whether the application is likely to remain stable under expected usage and identify any limits that require further testing.
8. Error Handling and Edge Cases — Test invalid inputs, missing data, unexpected requests, failed API calls, network interruptions, permission errors, and other unusual scenarios. Check whether the system handles failures safely and consistently.
9. Dependencies and Configuration — Review package dependencies, versions, environment configurations, required services, build settings, and other potential compatibility or deployment issues. Identify known risks and misconfigurations without changing anything.
10. Deployment and Production Readiness — Assess the production configuration, environment variables, build process, logging, monitoring, error reporting, backup and recovery considerations, and other requirements relevant to a safe deployment.

- Do not modify, fix, or refactor anything during this assessment.
- Do not create, delete, rename, or overwrite files.
- Do not change environment variables, database schemas, permissions, configurations, or deployment settings.
- Do not perform destructive operations, reset databases, delete data, or run tests that could disrupt existing services.
- Do not expose, print, or include actual passwords, API keys, tokens, or other secrets in your report.
- Use existing tests and safe, appropriate testing methods wherever possible.
- Distinguish between issues confirmed through testing, issues identified through code inspection, and potential risks that still require verification.
- If a test cannot be performed because of missing access, credentials, tools, dependencies, or environmental limitations, document the limitation instead of assuming the test passed.
- Keep a clear record of what was inspected, what was tested, what was not tested, and the results of each check.
- Do not claim that everything has been checked or that the system is secure and deployment-ready unless the available evidence supports that conclusion.
  After completing the review, provide a detailed report containing:

1. Overall Deployment Readiness — State whether the project appears ready for deployment, is not ready for deployment, or requires further verification. Explain the reasons behind your conclusion.
2. Inspection and Testing Coverage — List the files, components, features, APIs, and other areas inspected or tested. Clearly identify anything that was skipped or could not be verified.
3. Test Results — Report the tests performed, their results, any failures, and the evidence supporting your findings.
4. Issues and Risks Identified — List all discovered bugs, vulnerabilities, configuration problems, performance concerns, and other issues. Assign a severity level, explain the potential impact, and identify the affected components where possible.
5. Multi-User and Scalability Assessment — Explain how well the system is expected to handle simultaneous users, what was actually tested, what limitations were found, and what additional testing may be necessary.
6. Security Assessment — Summarize the security checks performed, confirmed vulnerabilities, potential weaknesses, and areas requiring further investigation.
7. Unverified Areas and Limitations — List anything that could not be tested or conclusively verified, explain why, and state what evidence or access would be needed.
8. Recommended Next Steps — Provide a prioritized list of recommended fixes, improvements, additional tests, and investigations. Explain why each is necessary and which issues should be addressed first. Recommend the actions only; do not execute them.
9. Final Deployment Checklist — Provide a checklist of the requirements that should be satisfied before the project is considered ready for production.
   The purpose of this assessment is to understand the actual condition of the project before making any changes or proceeding with deployment. I want a thorough, honest, evidence-based evaluation that identifies as many existing and potential problems as possible.
   For this stage, do not implement any fixes or make any changes. Complete the inspection and testing, present your findings, and recommend what should be done next. Wait for my approval before performing any modifications or corrective actions.

10. Address primary-login throttling and account enumeration.
11. Review the tracked database exports and historical-data exposure.
12. Correct the small validation and empty-year UI issues.
13. Resolve SMTP and provision shared Redis.
14. Perform hosted smoke, load, monitoring, and recovery checks using fictitious client data.

Set-Location 'C:\Users\Romul\SAFEBOOKS'
& .\.venv\Scripts\python.exe -B 'C:\Users\Romul\.codex\visualizations\2026\09\14\01a09dc4-1d59-72e0-aeda-9d1ef720952f\reset_local_admin_once.py'

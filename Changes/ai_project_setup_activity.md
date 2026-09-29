# SafeBooks AI Project Setup Activity

## Why this document exists

This is a simple reminder of the AI-project-setup activity. It does not change how SafeBooks works. Its purpose is to help me remember what the setup files are for and what still needs to be completed.

## What we have completed

We created a separate Git branch called `feature-a`. This keeps activity work separate from `main`, which protects the main SafeBooks project.

We also created three project-guidance files in the SafeBooks root folder:

| File | What it means in simple words |
| --- | --- |
| `knowledge.md` | The SafeBooks handbook. It explains what the project is, its technology, folders, workflows, security, configuration, and testing. |
| `AGENTS.md` | The safety rules for coding assistants. It explains how an AI must work carefully without breaking client data, financial records, security, or existing features. |
| `CLAUDE.md` | A short guide for Claude Code. It tells Claude to read `knowledge.md` and follow the safety rules in `AGENTS.md`. |

## How the three files work together

1. An AI reads `knowledge.md` to understand SafeBooks.
2. The AI reads `AGENTS.md` to understand the rules it must follow.
3. If the AI tool is Claude Code, it can read `CLAUDE.md` to follow the same SafeBooks guidance.

Codex mainly benefits from `knowledge.md` and `AGENTS.md`. `CLAUDE.md` was created because the activity asked for compatibility with Claude Code too.

## Important safety idea

These files are instructions and documentation only. They do not change SafeBooks pages, databases, client records, authentication, or financial calculations.

When future changes are requested, an AI should first inspect the relevant SafeBooks files, make only the requested change, preserve unrelated features, and run the appropriate checks or tests.

## What is a skill?

A skill is a reusable set of instructions for a specific type of work. It helps an AI follow the same safe process every time it works on that part of SafeBooks.

A skill is **not** a SafeBooks feature. It does not add a page, button, database table, or user function. It is an AI work guide stored with the project. Codex reads a skill only when the user's request matches the skill description.

The structure copied from the earlier chat-project skill was:

1. Give the skill a clear name and description so the AI knows when to use it.
2. Tell the AI which project flow and files to inspect.
3. List important rules that must remain true.
4. Tell the AI to make a narrow change without affecting unrelated behavior.
5. Tell the AI how to verify the result.

We copied that useful structure, but replaced the React, Express, Socket.IO, chat-room, and message instructions with rules that match SafeBooks.

We created these two SafeBooks skills:

- **`safebooks-client-management`**: safely guides work on client creation, editing, status, validation, location selection, credentials, notifications, and client details.
- **`safebooks-financial-records`**: safely guides work on financial records, line items, periods, monetary totals, reports, analytics, forecasting dependencies, and permissions.

Each skill is stored in its own folder under `.agents/skills/` and contains a `SKILL.md`. The skill name and description help an AI decide when to use it. The remaining instructions explain which SafeBooks files to inspect, which rules must be preserved, and which tests should be run.

## Purpose of the two custom skills

### `safebooks-client-management`

Use this when the request concerns adding or editing clients, client status, validation, the Davao Region XI location selector, client credentials, notifications, or the client-details interface. Its purpose is to remind the AI to protect bookkeeper ownership, existing client data, API payloads, and every create/edit path.

### `safebooks-financial-records`

Use this when the request concerns financial records, line items, periods, amounts, totals, reports, analytics, or forecasting inputs. Its purpose is to remind the AI to protect ownership, use accurate decimal calculations, keep related database writes consistent, and check downstream reports and summaries.

## Purpose for the demonstration

The demonstration shows that SafeBooks has reusable AI guidance based on its real architecture. The skills themselves are the deliverable; no extra website feature must be created to demonstrate them.

A simple demonstration can be:

1. Open both `.agents/skills/<skill-name>/SKILL.md` files and show their names, descriptions, workflows, safety rules, and verification sections.
2. Ask Codex: `Use $safebooks-client-management to review the Add Client workflow.`
3. Explain that Codex selects the matching skill and follows its SafeBooks-specific checklist.
4. Ask a second example: `Use $safebooks-financial-records to review how record totals are calculated.`
5. Explain that this skill directs Codex to the financial service, models, dependent reports, and focused tests.

For a safe classroom demo, ask for a **review or explanation only**. This demonstrates the skill without changing application code or data.

The old `agent/skills/SKILL.md` described a React and Socket.IO chat project. It was removed because those instructions do not apply to SafeBooks and could mislead an AI.

## External skill installed

We installed **`security-best-practices`** from OpenAI's curated skills repository and copied it into `.agents/skills/security-best-practices/`.

This is different from the two custom skills:

- The two `safebooks-*` skills were written specifically for this project.
- `security-best-practices` was created and maintained by an external provider, OpenAI.

### Purpose of the external skill

The external skill helps an AI perform security-focused work for supported languages and frameworks. It includes a Django-specific reference covering authentication, authorization, CSRF, sessions and cookies, templates and XSS, SQL safety, secrets, file handling, redirects, security headers, and production configuration.

It does not automatically scan, change, or secure SafeBooks merely because it is installed. Its description says it should be used when the user explicitly requests secure coding guidance, a security review, or a security report.

### Safe demonstration

A safe review-only demonstration prompt is:

`Use $security-best-practices to explain which Django security areas should be reviewed before deploying SafeBooks. Do not modify files.`

For the demo, explain that Codex will identify Django as the backend framework, load the included Django security reference, inspect relevant project files, and report evidence-based findings. Actual fixes should only be made after the findings are reviewed and the user asks for changes.

## Activity completion status

The requested setup steps are now present on the `feature-a` branch:

1. A separate feature branch is being used.
2. `knowledge.md`, `AGENTS.md`, and `CLAUDE.md` were created.
3. Two custom SafeBooks skills were created.
4. One external OpenAI skill was installed and verified as relevant to Django and SafeBooks.

These files are currently project changes on the feature branch. They have not been committed or merged into `main` as part of this activity.

## Where the external skill came from

The `security-best-practices` skill was downloaded from OpenAI's official curated skills repository:

`https://github.com/openai/skills/tree/main/skills/.curated/security-best-practices`

It was copied into this SafeBooks project at:

`.agents/skills/security-best-practices/`

The entire skill package was kept, including its main `SKILL.md`, license, metadata, and framework-specific security references. One of those references is specifically for Python and Django, which is why the skill is relevant to SafeBooks.

## Simple presentation script

> Good day. For this activity, I prepared my SafeBooks project so that AI coding assistants can understand it and work on it more safely.
>
> First, I created and used a separate Git branch called `feature-a`. The purpose of the branch is to keep the activity changes separate from the main version of SafeBooks. This protects the `main` branch while I review and test the work.
>
> Next, I created three guidance files. The first is `knowledge.md`. I describe this as the SafeBooks handbook because it explains the project's purpose, technologies, folders, workflows, configuration, and testing. The second is `AGENTS.md`. This is the safety rulebook for AI coding assistants. It tells them to protect client ownership, financial records, credentials, security, and existing functionality. The third is `CLAUDE.md`. It is a short compatibility guide that tells Claude Code to read the project knowledge and follow the same safety rules.
>
> After that, I created two custom skills based on my project. A skill is not a website feature. It is a reusable instruction guide that helps an AI follow the correct process for a particular kind of development task.
>
> The first custom skill is `safebooks-client-management`. It guides work involving client creation, editing, validation, location selection, credentials, notifications, and client details. The second is `safebooks-financial-records`. It guides work involving financial records, line items, periods, monetary totals, reports, analytics, and forecasting dependencies.
>
> I based these skills on the structure of the original example skill. I kept the useful pattern: give the skill a clear description, identify the files and workflow to inspect, preserve important rules, implement changes narrowly, and verify the result. I removed the old React, Express, Socket.IO, and chat instructions because they did not apply to my Django SafeBooks project.
>
> Finally, I installed an external skill called `security-best-practices` from OpenAI's official curated skills repository. I selected it because SafeBooks handles authentication, sessions, client credentials, and financial information. It includes security guidance specifically for Django.
>
> Installing a skill does not automatically change or scan my application. It only gives the AI additional guidance when I explicitly request a matching task. For example, I can ask Codex to use the security skill to explain which Django security areas should be reviewed before deployment, without modifying any files.
>
> In summary, the branch protects the main project, `knowledge.md` explains SafeBooks, `AGENTS.md` gives general safety rules, `CLAUDE.md` supports Claude Code, the two custom skills guide SafeBooks-specific work, and the downloaded security skill provides trusted Django security guidance. These are development-support files, so they do not add or change any user-facing SafeBooks feature.

## Short demonstration prompts

Use review-only prompts during the demonstration so no application data or code is changed:

1. `Use $safebooks-client-management to review and explain the Add Client workflow. Do not modify files.`
2. `Use $safebooks-financial-records to explain how financial-record totals are calculated. Do not modify files.`
3. `Use $security-best-practices to explain which Django security areas should be reviewed before deploying SafeBooks. Do not modify files.`

## Possible questions and simple answers

**Is a skill a new SafeBooks feature?**  
No. A skill is an instruction guide for an AI assistant. It does not appear in the SafeBooks interface and does not change the database.

**Why are there two custom skills?**  
The activity requires two skills based on the project. Client management and financial records are two important SafeBooks areas with different workflows and safety rules.

**Why was the old skill replaced?**  
It described a React and Socket.IO chat project. SafeBooks uses Django and has different data, security, and testing requirements.

**Why install the security skill?**  
SafeBooks handles sensitive account and financial information. OpenAI's external skill provides Django-specific security guidance that can support a future security review.

**Did these files change the SafeBooks application?**  
No. They are documentation and AI guidance files only. They do not change pages, database records, financial calculations, or authentication behavior.

## Final plain review

For this activity, we first used the `feature-a` branch so our work stayed separate from the main SafeBooks project.

We then created three guidance files:

- `knowledge.md` explains what SafeBooks is and how the project works.
- `AGENTS.md` tells AI assistants how to work safely in the project.
- `CLAUDE.md` gives Claude Code the same project guidance.

Next, we created two custom skills based on SafeBooks. The client-management skill guides AI work involving clients, while the financial-records skill guides work involving records, amounts, reports, and related calculations. These skills are AI instructions, not new website features.

Lastly, we downloaded OpenAI's `security-best-practices` skill. It provides additional Django security guidance when we explicitly request a security review.

In short, this activity prepared SafeBooks for safer and more organized AI-assisted development. It did not change the application's existing functionality.

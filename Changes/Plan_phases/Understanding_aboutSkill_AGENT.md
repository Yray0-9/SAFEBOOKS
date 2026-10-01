# SafeBooks Skills Guide

## Overview

The current understanding of Skills is mostly correct, with one important clarification:

> A project should not create one Skill for every individual feature.

Skills work best as focused, reusable playbooks for meaningful categories of work, rather than as one file for every page, button, modal, dropdown, or small feature.

For SafeBooks, the goal should be to create a small number of well-defined Skills that provide specialized instructions where they are genuinely useful, while keeping project-wide rules in **`AGENTS.md`**.

## 1. What Is a Skill?

A Skill is a reusable package of instructions that teaches an AI coding agent how to handle a particular category of work.

A Skill can tell the agent:

- When the Skill applies.
- Which files, directories, and workflows should be inspected.
- What development process should be followed.
- Which project rules or invariants must be protected.
- Which mistakes or unsafe approaches must be avoided.
- Which commands, tests, or validation steps should be performed.
- How the result should be reported.

A Skill can also contain supporting resources such as:

- Reference documentation.
- Scripts.
- Templates.
- Examples.
- Checklists.
- Other files required for the specialized workflow.

The purpose of a Skill is to give the AI agent a repeatable and specialized process for a particular category of work.

> Important: A Skill is not the application itself. It is an instruction and resource package that helps the AI agent work on the application correctly.

## 2. What a Skill Does Not Do

A Skill does not:

- Add a user-facing feature to SafeBooks.
- Automatically modify the application simply because the Skill exists.
- Replace application code.
- Replace careful code inspection.
- Replace testing and validation.
- Permanently remember everything about the project.
- Guarantee that the agent will always produce correct code.
- Eliminate the need for the agent to understand the existing implementation.

Instead, a Skill provides the agent with a better and more consistent process when the relevant type of task appears.

## 3. What Is `SKILL.md`?

The conventional filename for the main Skill instruction file is:

**`SKILL.md`**

A Skill normally exists inside its own directory.

Example:

**`.agents/skills/safebooks-client-management/SKILL.md`**

The Skill directory can also contain additional supporting resources when necessary, such as references, scripts, templates, examples, and other documentation.

## 4. Structure of a `SKILL.md`

A typical **`SKILL.md`** contains two major parts:

1. Skill metadata.
2. Skill instructions.

### 4.1 Skill Metadata

The beginning of the file defines metadata describing the Skill.

Example:

---
name: safebooks-client-management
description: Use for SafeBooks client creation, editing, location, validation, credentials, and client-detail workflows.
---

The description is especially important because it helps the AI coding agent determine when the Skill is relevant.

The description should therefore be:

- Specific enough to identify the appropriate tasks.
- Broad enough to cover the actual scope of the Skill.
- Focused on the type of work rather than one tiny UI element.

### 4.2 Skill Instructions

After the metadata, the file contains the detailed instructions that should be followed when the Skill is relevant.

Example:

# SafeBooks Client Management

When working on client-management functionality:

1. Inspect the relevant client routes, views, services, models, templates, JavaScript, and tests.
2. Preserve existing client ownership rules.
3. Preserve existing API payload structures unless the task explicitly requires a change.
4. Verify validation and error-handling behavior.
5. Check create, edit, save, cancel, reset, and failure paths where applicable.
6. Run the relevant tests and validation checks.
7. Report any checks that could not be completed.

The exact instructions should depend on the specialized domain being covered.

## 5. How the Agent Uses a Skill

A Skill can be selected when the agent determines that the current task matches the Skill's description.

For example:

Use **`$safebooks-client-management`** to review the Add Client workflow.

This explicitly tells the agent to use the client-management Skill.

The important concept is:

> Skills should be activated because the work matches their purpose, not simply because the project contains a particular feature.

## 6. `AGENTS.md` vs. `SKILL.md`

This is one of the most important distinctions for the SafeBooks project.

| **File**        | **Purpose**                                                                                | **When It Applies**                      |
| --------------- | ------------------------------------------------------------------------------------------ | ---------------------------------------- |
| **`AGENTS.md`** | Permanent project-wide instructions, architecture, safety rules, and development standards | Generally applies to SafeBooks work      |
| **`SKILL.md`**  | Specialized instructions for a particular category of work                                 | Applies when the task matches that Skill |

A useful way to think about the distinction is:

> **`AGENTS.md`** = How to work safely anywhere in SafeBooks.

> **`SKILL.md`** = How to perform one specialized kind of SafeBooks work.

## 7. What Belongs in `AGENTS.md`?

Instructions that apply to almost every development task should primarily belong in **`AGENTS.md`**.

Examples:

- Preserve existing functionality.
- Avoid unrelated changes.
- Inspect relevant code before editing.
- Follow the existing architecture.
- Do not introduce unnecessary dependencies.
- Preserve existing APIs unless a change is explicitly required.
- Protect existing data.
- Never expose credentials, secrets, or sensitive information.
- Run appropriate checks and tests.
- Explain what was changed.
- Explain what could not be tested.
- Avoid unnecessary rewrites.
- Consider backward compatibility.
- Keep changes focused on the requested task.

These are project-wide development rules.

Putting them into every Skill would create unnecessary duplication.

## 8. What Belongs in a Skill?

A Skill should provide instructions that require specialized knowledge, workflows, or safeguards.

Examples include:

- Client ownership and client-payload rules.
- Financial decimal and total-calculation rules.
- Deployment procedures.
- Database migration workflows.
- Security-review methodology.
- Accessibility-review procedures.
- Specialized testing procedures.
- Reporting and forecasting rules.

A Skill should answer this question:

> What is special about this category of work that the AI agent needs to know?

If the answer is simply:

> Work carefully, preserve existing functionality, inspect the code first, and test your changes.

Then that instruction probably belongs in **`AGENTS.md`**, not in every individual Skill.

## 9. Should Every Feature Have Its Own Skill?

### No.

It would normally be unnecessary to create separate Skills such as:

- **`add-client-modal`**
- **`edit-client-button`**
- **`password-strength-meter`**
- **`dashboard-filter`**
- **`location-dropdown`**

These represent individual features or UI components rather than meaningful categories of work.

Creating a Skill for every small feature can result in:

- Too many Skills.
- Very narrow descriptions.
- Overlapping instructions.
- Difficulty determining which Skill applies.
- Repeated content.
- More maintenance work.
- Skills becoming outdated when features change.
- Less clarity about the actual purpose of each Skill.

The goal should be useful specialization, not maximum fragmentation.

## 10. When Is a Feature-Specific Skill Justified?

A feature-specific Skill can be justified when the feature represents a substantial, repeatable, specialized workflow.

For example, a complex deployment process might involve:

- Environment validation.
- Database migrations.
- Static-file handling.
- Backups.
- Security checks.
- Configuration validation.
- Deployment verification.
- Rollback procedures.

That could reasonably justify a dedicated deployment Skill because the workflow is substantial, repeatable, and specialized.

The important question is not:

> Is this a feature?

Instead, ask:

> Does this area of work require a distinct, reusable process that the AI agent needs to follow?

## 11. When Should Skills Be Separate?

Create separate Skills when the areas have clearly different:

- Triggers or user requests.
- Files and architecture.
- Risks and invariants.
- Required expertise.
- Verification procedures.
- Development workflows.
- Specialized rules.

For SafeBooks, client management and financial records are meaningfully different domains.

### Client Management

Client-management work may need to protect:

- Client ownership.
- Client identity.
- Client credentials.
- Locations.
- Validation rules.
- Client API payloads.
- Client details.
- Client notifications.

### Financial Records

Financial-record work may need to protect:

- Monetary calculations.
- Decimal precision.
- Periods.
- Line items.
- Transactions.
- Database consistency.
- Reports.
- Analytics.
- Forecasting inputs.
- Authorization.

Because these domains have different risks, rules, workflows, and validation requirements, keeping them as separate Skills is reasonable.

## 12. When Should Skills Be Combined?

Skills should be combined when:

- They are triggered by almost the same requests.
- They inspect mostly the same files.
- They contain heavily duplicated instructions.
- One Skill is too small to be useful independently.
- They are almost always required together.
- Their differences can be expressed as sections within one broader Skill.

For example, these separate Skills would probably be unnecessarily fragmented:

- **`add-client`**
- **`edit-client`**
- **`client-location`**
- **`client-validation`**
- **`client-details`**

A better approach would generally be:

**`safebooks-client-management`**

with sections covering:

- Client Creation.
- Client Editing.
- Client Location.
- Client Validation.
- Client Details.

This provides one reusable domain-level Skill instead of many small Skills.

## 13. Are the Current SafeBooks Skills Too Specific?

Not necessarily.

The current Skills are not actually organized as one Skill per feature. They represent two broader project domains:

1. **`safebooks-client-management`**
2. **`safebooks-financial-records`**

### `safebooks-client-management`

This Skill can cover multiple related areas, including:

- Client creation.
- Client editing.
- Client status.
- Client validation.
- Location selection.
- Credentials.
- Notifications.
- Client details.

### `safebooks-financial-records`

This Skill can cover a larger financial domain, including:

- Financial records.
- Line items.
- Periods.
- Transactions.
- Monetary totals.
- Reports.
- Analytics.
- Forecasting dependencies.
- Authorization.
- Database consistency.

Therefore, the current separation has a reasonable technical basis.

## 14. Should Everything Be Combined Into One Skill?

It would be possible to create something such as:

**`safebooks-development`**

However, this could create another problem.

If the Skill becomes broad enough to describe nearly every type of SafeBooks development, it may start duplicating the contents of **`AGENTS.md`**.

That would reduce the benefit of having specialized Skills.

The purpose of Skills is not to create a second copy of the entire project instruction manual.

Instead, the structure should generally be:

```text
AGENTS.md
├── Project-wide rules
└── Specialized Skills
    ├── Client Management
    ├── Financial Records
    ├── Security Review
    └── Deployment
```

This separation keeps responsibilities clear.

## 15. Where Should Repeated Development Instructions Go?

A common instruction might be:

> "Do this properly and professionally. Take your time, avoid unnecessary changes, and do not break existing functionality."

The intention behind this instruction is good.

However, terms such as "properly", "professionally", and "carefully" can be subjective.

AI agents generally benefit more from concrete, testable instructions.

Instead of:

> Do this properly and professionally.

Use instructions such as:

- Inspect the affected workflow before editing.
- Modify only files required by the task.
- Preserve existing selectors, API payloads, endpoints, and stored data unless a change is explicitly required.
- Do not rewrite unrelated code.
- Preserve existing behavior outside the requested scope.
- Check create, edit, save, cancel, reset, and error paths where applicable.
- Run relevant checks and tests.
- Report any validation or test that could not be completed.

These instructions are much more actionable.

## 16. Why This Matters

The goal of an instruction system is not simply to tell the AI:

> "Be careful."

The goal is to define what being careful actually means within the project.

For example:

> "Do not break existing functionality."

Can be transformed into:

- Preserve existing API contracts.
- Preserve database relationships.
- Avoid modifying unrelated components.
- Verify existing workflows after making changes.
- Run relevant tests.
- Check both success and error paths.

This gives the agent concrete behavior to follow.

## 17. Recommended SafeBooks Structure

A sensible starting structure for SafeBooks is:

```text
AGENTS.md

.agents/
└── skills/
    ├── safebooks-client-management/
    │   └── SKILL.md
    ├── safebooks-financial-records/
    │   └── SKILL.md
    └── security-best-practices/
        └── SKILL.md
```

The responsibilities should be divided as follows.

### `AGENTS.md`

Contains:

- Project architecture.
- Global development rules.
- General safety requirements.
- Coding standards.
- Testing expectations.
- Change-management rules.
- General instructions that apply to most or all SafeBooks work.

### `safebooks-client-management/SKILL.md`

Contains:

- Client-management workflows.
- Client-specific invariants.
- Ownership rules.
- Client payload requirements.
- Client validation rules.
- Client-specific testing and verification.

### `safebooks-financial-records/SKILL.md`

Contains:

- Financial-record workflows.
- Monetary calculation rules.
- Decimal and precision requirements.
- Financial database rules.
- Reporting dependencies.
- Financial-specific validation.

### `security-best-practices/SKILL.md`

Contains:

- Security-review methodology.
- Authentication and authorization considerations.
- Secret-handling rules.
- Security validation procedures.
- Security-specific references and checklists.

## 18. Practical Decision Rule

When deciding whether something should become a new Skill, use this question:

> Does this represent a meaningful category of work with its own repeatable workflow, specialized rules, risks, and validation process?

If yes, a separate Skill may be appropriate.

If no, it probably belongs in:

- **`AGENTS.md`**, if it is a general project rule; or
- An existing Skill, if it is part of an already-defined specialized domain.

A simple decision model is:

Is the instruction applicable to most SafeBooks work?

YES → **`AGENTS.md`**

NO → Does it belong to an existing specialized domain?

YES → Existing **`SKILL.md`**

NO → Does it represent a meaningful, repeatable, specialized workflow?

YES → Consider a new **`SKILL.md`**

NO → Do not create a new Skill.

## 19. Final Principle

The purpose of the SafeBooks instruction system should be clarity, consistency, and maintainability.

Do not create Skills simply because a feature exists.

Instead:

```text
AGENTS.md
↓
General rules for working safely on SafeBooks

SKILL.md
↓
Specialized playbook for a meaningful category of work
```

The current **`safebooks-client-management`** and **`safebooks-financial-records`** Skills already represent broader domains rather than individual features, so their separation is reasonable.

There is currently no need to create a separate Skill for every SafeBooks feature, page, button, modal, or component.

The preferred approach is to:

1. Keep project-wide rules in **`AGENTS.md`**.
2. Keep domain-specific rules in specialized Skills.
3. Combine Skills that are too small, overlapping, or heavily duplicated.
4. Create new Skills only when a genuinely distinct and reusable workflow exists.
5. Keep Skills focused enough that the agent can clearly determine when they are relevant.
6. Avoid duplicating the same instructions across **`AGENTS.md`** and multiple Skills.
7. Convert vague expectations into concrete, actionable instructions whenever possible.

This structure gives the AI coding agent both:

- The general rules it should follow throughout SafeBooks.
- The specialized knowledge it needs for particular categories of work.

The result should be a Skill system that is focused rather than fragmented, reusable rather than repetitive, and specific rather than unnecessarily broad.
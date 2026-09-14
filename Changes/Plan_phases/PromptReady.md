# Capstone Project AI Prompt (Codex AI Activity)

## Activity Overview
- **Prompt Structure Used**: **C-O-R-C-E** (*Context - Objective - Requirements - Constraints - Expected Output*)
- **Target Application**: **SafeBooks** (Bookkeeper Financial Record & Account Management System)
- **Execution Mode**: **Autonomous / Direct File Editing** (instructs the AI to perform and apply the work directly to the project files instead of just printing code blocks for manual copy-pasting).

---

## [Autonomous Action Version] Ready-to-Copy Prompt for Codex AI

```text
Context: "I'm working on a Django financial management web application called SafeBooks where bookkeepers manage financial records and account settings."

Objective: "Directly implement a real-time password strength meter bar and live validation updates in the existing 'Change Password' modal on the Settings page (#settingsChangePasswordModal)."

Requirements: "As the user types into #settingsNewPassword, evaluate the entered password in real-time. Dynamically update a visual multi-segment strength bar (Weak / Medium / Strong) with smooth color transitions, and toggle the active state of the existing requirement chips (length, uppercase, lowercase, number, symbol) without interfering with typing."

Constraints: "STRICT NON-BREAKING & AUTONOMOUS REQUIREMENT: Do NOT modify existing backend endpoints, Django view logic, or database models. Do NOT alter existing form submission handlers, password show/hide toggle buttons, or the disabled input styling (#eaecef). Do NOT just output code blocks for manual copy-pasting - directly edit and apply the modifications to the project files."

Expected output: "Directly apply the exact edits into templates/base/settings.html, static/css/settings.css, and static/js/settings_page.js, and provide a short summary of the applied changes."
```

---

## Breakdown of the 5-Part Structure (For Professor Submission)

| Component | Content in Prompt | Purpose for Codex AI |
| :--- | :--- | :--- |
| **Context** | *"I'm working on a Django financial management web application called SafeBooks where bookkeepers manage financial records and account settings."* | Sets the exact project stack and domain so the AI understands the existing codebase. |
| **Objective** | *"Directly implement a real-time password strength meter bar and live validation updates in the existing 'Change Password' modal on the Settings page (#settingsChangePasswordModal)."* | Specifies an active, direct implementation goal rather than asking for advice or explanation. |
| **Requirements** | *"As the user types into #settingsNewPassword, evaluate the entered password in real-time. Dynamically update a visual multi-segment strength bar (Weak / Medium / Strong) with smooth color transitions, and toggle the active state of the existing requirement chips (length, uppercase, lowercase, number, symbol) without interfering with typing."* | Outlines the exact UI and behavioral expectations clearly and concisely. |
| **Constraints** | *"STRICT NON-BREAKING & AUTONOMOUS REQUIREMENT: Do NOT modify existing backend endpoints, Django view logic, or database models. Do NOT alter existing form submission handlers, password show/hide toggle buttons, or the disabled input styling (#eaecef). Do NOT just output code blocks for manual copy-pasting - directly edit and apply the modifications to the project files."* | **Zero-Breaking & Action Guarantee**: Forbids breaking any existing features and explicitly instructs the AI to do the work rather than giving homework to the user. |
| **Expected output** | *"Directly apply the exact edits into templates/base/settings.html, static/css/settings.css, and static/js/settings_page.js, and provide a short summary of the applied changes."* | Designates the exact target files so the AI acts on the workspace files directly. |

---

## Quick Tips for Getting Codex / AI to Apply Changes Automatically

1. **Use Agent / Edit Mode**: If your Codex/AI tool in the IDE has a mode toggle (e.g. *Agent*, *Edit*, or *Composer* instead of standard *Chat*), select **Agent/Edit Mode**. This gives the AI permission to modify files directly on your disk.
2. **Provide File Names**: Because the prompt specifies `templates/base/settings.html`, `static/css/settings.css`, and `static/js/settings_page.js`, the AI knows exactly where to go and won't get lost.

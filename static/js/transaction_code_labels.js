// Display only. Keep the original code for submissions, grouping, and tax rules.
window.SafeBooksTransactionCodeLabel = (value) =>
    String(value ?? "").replace(/^\s*BIR\s+Form\s+(\d[\da-z]+)\s*$/i, "$1");

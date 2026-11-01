(() => {
    const get = id => document.getElementById(id);
    const form = get("verificationProofForm"), type = get("verificationDocumentType");
    const other = get("verificationOtherDocument"), name = get("verificationDocumentName");
    const file = get("verificationProofFile"), clear = get("verificationClearSelection"), submit = get("verificationSubmitProof");
    const notice = get("verificationSubmissionNotice"), status = get("verificationProofStatus"), savedLink = get("verificationSavedDocument");
    if (![form, type, other, name, file, clear, submit, notice, status, savedLink].every(Boolean)) return;
    let saved = null, busy = false, uncertain = false;
    try { saved = JSON.parse(get("verificationSavedProof").textContent); } catch (_) { uncertain = true; }
    const update = () => {
        other.hidden = type.value !== "other";
        name.disabled = other.hidden || busy;
        name.required = !other.hidden;
        type.disabled = file.disabled = busy;
        clear.hidden = !type.value && !file.files.length && !name.value;
        clear.disabled = busy;
        submit.textContent = busy ? "Submitting…" : saved ? "Replace proof" : "Submit proof";
        submit.disabled = busy || uncertain || !type.value || !file.files.length || (!other.hidden && !name.value.trim());
    };
    [type, file].forEach(node => node.addEventListener("change", update));
    name.addEventListener("input", update);
    clear.addEventListener("click", () => {
        type.value = name.value = file.value = "";
        update(); type.focus();
    });
    form.addEventListener("submit", async event => {
        event.preventDefault();
        if (busy || uncertain || !form.reportValidity()) return;
        if (!file.files.length || file.files[0].size > 5 * 1024 * 1024) {
            notice.textContent = "Choose one JPG, PNG or PDF up to 5 MB.";
            return;
        }
        const data = new FormData(form);
        data.set("revision", saved ? saved.revision : "");
        busy = true; update(); notice.textContent = "Submitting proof…";
        let responseStatus = 0;
        try {
            const response = await fetch(form.getAttribute("action"), {
                method: "POST", body: data, credentials: "same-origin", headers: { Accept: "application/json" },
            });
            responseStatus = response.status;
            const result = await response.json();
            if (!response.ok || !result.ok) {
                uncertain = response.status >= 500 || response.status === 409;
                notice.textContent = result.message || "Submission was not confirmed. Reload to check its status.";
                return;
            }
            if (!result.proof || !result.proof.revision || !result.proof.download_url) throw new Error("Unconfirmed response");
            saved = result.proof;
            status.textContent = "Submitted";
            savedLink.href = saved.download_url; savedLink.hidden = false;
            notice.textContent = "Proof submitted for admin review. A new submission replaces it.";
            type.value = name.value = file.value = "";
        } catch (_) {
            console.warn(`Proof submission could not be confirmed (HTTP ${responseStatus}).`);
            uncertain = true;
            notice.textContent = "Submission was not confirmed. Reload to check its status before trying again.";
        } finally { busy = false; update(); }
    });
    update();
})();

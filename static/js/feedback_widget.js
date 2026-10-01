(function () {
    const widget = document.getElementById("bookkeeperFeedbackWidget");
    const modalElement = document.getElementById("bookkeeperFeedbackModal");
    const trigger = document.getElementById("bookkeeperFeedbackTrigger");
    const form = document.getElementById("bookkeeperFeedbackForm");
    const messageInput = document.getElementById("bookkeeperFeedbackMessage");
    const characterCount = document.getElementById("bookkeeperFeedbackCharacterCount");
    const submitButton = document.getElementById("bookkeeperFeedbackSubmit");
    const statusElement = document.getElementById("bookkeeperFeedbackStatus");
    const toastContainer = document.getElementById("uiToastContainer");
    const shared = window.SafeBooksShared || null;

    if (!widget || !modalElement || !trigger || !form || !messageInput || !submitButton) {
        return;
    }

    const submitUrl = String(widget.dataset.feedbackSubmitUrl || "").trim();
    const minimumLength = 10;
    const maximumLength = 2000;
    let submitting = false;
    let allowClose = false;

    const parseJsonSafe = async (response) => {
        if (shared && typeof shared.parseJsonSafe === "function") {
            return shared.parseJsonSafe(response);
        }
        try {
            return await response.json();
        } catch (error) {
            return null;
        }
    };

    const getCsrfToken = () => {
        if (shared && typeof shared.getCookieValue === "function") {
            return shared.getCookieValue("csrftoken");
        }
        return "";
    };

    const setStatus = (message) => {
        if (statusElement) {
            statusElement.textContent = String(message || "");
        }
    };

    const updateCharacterCount = () => {
        if (characterCount) {
            characterCount.textContent = `${messageInput.value.length} / ${maximumLength}`;
        }
    };

    const setSubmitting = (isSubmitting) => {
        submitting = isSubmitting;
        submitButton.disabled = isSubmitting;
        submitButton.classList.toggle("is-loading", isSubmitting);
        form.querySelectorAll("input, textarea, button[data-bs-dismiss='modal']").forEach((control) => {
            control.disabled = isSubmitting;
        });
    };

    const resetForm = () => {
        form.reset();
        messageInput.classList.remove("is-invalid");
        setStatus("");
        updateCharacterCount();
    };

    const getPageTitle = () => {
        const heading = document.querySelector(".dashboard-page-title");
        const headingText = heading ? String(heading.textContent || "").trim() : "";
        if (headingText) {
            return headingText;
        }
        return String(document.title || "SafeBooks page").replace(/^SafeBooks\s*\|\s*/i, "").trim();
    };

    const showSuccessToast = (message) => {
        if (shared && typeof shared.showToast === "function") {
            shared.showToast(toastContainer, message, "success", { delay: 4200 });
        }
    };

    messageInput.addEventListener("input", () => {
        messageInput.classList.remove("is-invalid");
        setStatus("");
        updateCharacterCount();
    });

    modalElement.addEventListener("shown.bs.modal", () => {
        window.setTimeout(() => messageInput.focus(), 0);
    });

    modalElement.addEventListener("hide.bs.modal", (event) => {
        if (allowClose) {
            return;
        }

        if (submitting) {
            event.preventDefault();
            return;
        }

        if (!messageInput.value.trim()) {
            return;
        }

        const shouldDiscard = window.confirm("Discard your unsent feedback?");
        if (!shouldDiscard) {
            event.preventDefault();
        }
    });

    modalElement.addEventListener("hidden.bs.modal", () => {
        allowClose = false;
        trigger.focus();
    });

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        if (submitting) {
            return;
        }

        const message = messageInput.value.trim();
        if (message.length < minimumLength) {
            messageInput.classList.add("is-invalid");
            setStatus(`Please enter at least ${minimumLength} characters.`);
            messageInput.focus();
            return;
        }

        const selectedCategory = form.querySelector("input[name='feedbackCategory']:checked");
        if (!selectedCategory || !submitUrl) {
            setStatus("The feedback form is not available right now. Please refresh and try again.");
            return;
        }

        const csrfToken = getCsrfToken();
        const headers = { "Content-Type": "application/json" };
        if (csrfToken) {
            headers["X-CSRFToken"] = csrfToken;
        }

        setStatus("");
        setSubmitting(true);

        try {
            const response = await fetch(submitUrl, {
                method: "POST",
                credentials: "same-origin",
                headers,
                body: JSON.stringify({
                    category: selectedCategory.value,
                    message,
                    page_title: getPageTitle(),
                    page_path: window.location.pathname,
                }),
            });
            const payload = await parseJsonSafe(response);

            if (!response.ok || !payload || !payload.ok) {
                setStatus(
                    payload && payload.message
                        ? payload.message
                        : "We could not send your feedback right now. Your message is still here - please try again."
                );
                return;
            }

            const successMessage = payload.message || "Thank you - your feedback was sent to the SafeBooks developer.";
            allowClose = true;
            resetForm();

            if (window.bootstrap && window.bootstrap.Modal) {
                window.bootstrap.Modal.getOrCreateInstance(modalElement).hide();
            }
            showSuccessToast(successMessage);
        } catch (requestError) {
            setStatus("We could not send your feedback right now. Your message is still here - please try again.");
        } finally {
            setSubmitting(false);
        }
    });

    updateCharacterCount();
})();

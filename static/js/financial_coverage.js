(function (global) {
    "use strict";
    const months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
    const frequencies = ["monthly", "quarterly", "annually"];
    const parts = date => /^(\d{4})-(\d{2})-\d{2}$/.exec(String(date || ""));
    const label = (frequency, date, legacy = false) => {
        const match = parts(date);
        const month = match ? Number(match[2]) : 0;
        if (!month || month > 12) return ({ monthly: "This month", quarterly: "Whole quarter", annually: "Whole year" })[frequency] || "";
        const year = match[1];
        if (frequency === "annually") return `January–December ${year}`;
        if (frequency === "quarterly") {
            if (legacy && month % 3 !== 0) {
                const start = month - 3;
                return start < 0 ? `${months[start + 12]} ${Number(year) - 1}–${months[month - 1]} ${year}` : `${months[start]}–${months[month - 1]} ${year}`;
            }
            const start = Math.floor((month - 1) / 3) * 3;
            return `${months[start]}–${months[start + 2]} ${year}`;
        }
        return `${months[month - 1]} ${year} only`;
    };
    const options = (date, legacyFrequency, escape, savedFrequency = "", selectedFrequency = savedFrequency) => {
        const match = parts(date);
        const month = match ? Number(match[2]) : 0;
        const quarterAllowed = month >= 1 && month <= 12 && month % 3 === 0;
        // Only offer a new quarter at its ending month. Retain a selected quarter
        // as disabled if the date changes, so no saved/draft coverage is erased.
        const choices = frequencies.filter(frequency => {
            if (frequency === "quarterly") return quarterAllowed || selectedFrequency === "quarterly";
            return frequency !== "annually" || legacyFrequency === "annually" || savedFrequency === "annually";
        });
        return `<option value="">${legacyFrequency ? escape(label(legacyFrequency, date, true)) + " (saved)" : "Choose period"}</option>` +
            choices.map(frequency => `<option value="${frequency}"${frequency === "quarterly" && !quarterAllowed ? " disabled" : ""}>${escape(label(frequency, date))}</option>`).join("");
    };
    const validate = (frequency, date) => {
        // Null retains an existing entry's coverage, never reclassifies history.
        if (frequency == null) return "";
        if (typeof frequency !== "string" || !frequencies.includes(frequency)) return "Choose a valid covered period.";
        const match = parts(date);
        const month = match ? Number(match[2]) : 0;
        if (frequency === "quarterly" && month && month % 3 !== 0) {
            const end = Math.ceil(month / 3) * 3;
            return `For ${label(frequency, date)}, set Record Date to ${months[end - 1]} ${match[1]}.`;
        }
        if (frequency === "annually" && month !== 12) return "For a whole year, use December as the record month.";
        return "";
    };
    global.SafeBooksCoverage = { label, options, validate };
})(window);

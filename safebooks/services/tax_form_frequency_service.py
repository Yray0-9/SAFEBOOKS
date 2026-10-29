"""Stable forecast frequency metadata for the BIR choices already offered.

This identifies a form's schedule, not the period a payment actually covers.
None means the form alone does not establish a recurring forecast frequency.
Legacy/custom entries retain their existing fallback outside this module.

References for the existing form labels and versions:
https://www.bir.gov.ph/bir-forms
https://bir-cdn.bir.gov.ph/local/pdf/RMC%20No%2027-2018.pdf
https://efps.bir.gov.ph/eFPSFAQ.html
https://bir-cdn.bir.gov.ph/BIR/pdf/RMC%20No.%2048-2024.pdf
"""
import re


_MONTHLY = (
    "0619e", "0619f", "1600", "1600ptv2018", "1600vtv2018",
    "1601c", "1601cv2018", "1601e", "1601f", "1602", "2000v2018",
    "2550m", "2551m",
)
_QUARTERLY = (
    "1601eq", "1601fq", "1602q", "1602qv2018", "1603", "1603q", "1603qv2018",
    "1701q", "1701qv2018", "1702q", "1702qv2008c", "1702qv2018c",
    "2550q", "2550qv2024", "2551q", "2551qv2018",
)
_ANNUAL = (
    "1604c", "1604cf", "1604f", "1604e", "1604ev2018", "1700", "1700v2018",
    "1701", "1701a", "1701ms", "1701v2018", "1702", "1702ex", "1702exv2018",
    "1702exv2018c", "1702mx", "1702mxv2018", "1702mxv2018c", "1702rt",
    "1702rtv2018", "1702rtv2018c", "1707a", "1707av2021",
)
_WITHOUT_FIXED_FREQUENCY = (
    "0605", "1600wp", "1606", "1704", "1706", "1707", "1707v2018", "1707v2021",
    "1800", "1800v2018", "1801", "1801v2018", "2000", "2000ot", "2000otv2018",
    "2200a", "2200av2020", "2200an", "2200anv2018", "2200cv2018", "2200m",
    "2200mv2018", "2200p", "2200pv2020", "2200s", "2200t", "2200tv2020",
    "2552", "2552v2018", "2553",
)

TAX_FORM_FREQUENCIES = {
    **dict.fromkeys(_MONTHLY, "monthly"),
    **dict.fromkeys(_QUARTERLY, "quarterly"),
    **dict.fromkeys(_ANNUAL, "annually"),
    **dict.fromkeys(_WITHOUT_FIXED_FREQUENCY),
}


def standard_tax_form_frequency(type_code: str) -> tuple[bool, str | None]:
    """Return (recognized, frequency); never search an editable description.

    Match the entire saved code. Preserve version suffixes, which can identify
    a different form, and tolerate ordinary BIR prefixes, spacing and hyphens.
    """
    code = re.sub(r"^bir\s*form\s*", "", str(type_code or "").strip(), flags=re.I)
    code = re.sub(r"[\s-]+", "", code).lower()
    return code in TAX_FORM_FREQUENCIES, TAX_FORM_FREQUENCIES.get(code)

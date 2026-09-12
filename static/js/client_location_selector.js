const DAVAO_REGION_PROVINCES = [
    "Davao De Oro",
    "Davao Del Norte",
    "Davao Del Sur",
    "Davao Occidental",
    "Davao Oriental",
];

const DAVAO_DEL_NORTE_PROVINCE = "Davao Del Norte";
const DAVAO_DEL_NORTE_LOCATIONS = {
    "Asuncion": [
        "Binancian",
        "Buan",
        "Buclad",
        "Cabaywa",
        "Camansa",
        "Cambanogoy (Pob.)",
        "Camoning",
        "Canatan",
        "Concepcion",
        "Dona Andrea",
        "Magatos",
        "Napungas",
        "New Bantayan",
        "New Loon",
        "New Santiago",
        "Pamacaun",
        "Sagayen",
        "San Vicente",
        "Santa Filomena",
        "Sonlon",
    ],
    "Carmen": [
        "Alejal",
        "Anibongan",
        "Asuncion",
        "Cebulano",
        "Guadalupe",
        "Ising (Pob.)",
        "La Paz",
        "Mabaus",
        "Mabuhay",
        "Magsaysay",
        "Mangalcal",
        "Minda",
        "New Camiling",
        "Salvacion",
        "San Isidro",
        "Santo Nino",
        "Taba",
        "Tibulao",
        "Tubod",
        "Tuganay",
    ],
    "Kapalong": [
        "Capungagan",
        "Florida",
        "Gabuyan",
        "Gupitan",
        "Katipunan",
        "Luna",
        "Mabantao",
        "Mamacao",
        "Maniki",
        "Pag-asa",
        "Sampao",
        "Semong",
        "Sua-on",
        "Tiburcia",
    ],
    "New Corella": [
        "Cabidianan",
        "Carcor",
        "Del Monte",
        "Del Pilar",
        "El Salvador",
        "Limba-an",
        "Macgum",
        "Mambing",
        "Mesaoy",
        "New Bohol",
        "New Cortez",
        "New Sambog",
        "Patrocenio",
        "Poblacion",
        "San Jose",
        "San Roque",
        "Santa Cruz",
        "Santa Fe",
        "Santo Nino",
        "Suawon",
    ],
    "City of Panabo": [
        "A. O. Floirendo",
        "Buenavista",
        "Cacao",
        "Cagangohan",
        "Consolacion",
        "Dapco",
        "Datu Abdul Dadia",
        "Gredu (Pob.)",
        "J.P. Laurel",
        "Kasilak",
        "Katipunan",
        "Katualan",
        "Kauswagan",
        "Kiotoy",
        "Little Panay",
        "Lower Panaga",
        "Mabunao",
        "Maduao",
        "Malativas",
        "Manay",
        "Nanyo",
        "New Malaga",
        "New Malitbog",
        "New Pandan (Pob.)",
        "New Visayas",
        "Quezon",
        "Salvacion",
        "San Francisco (Pob.)",
        "San Nicolas",
        "San Pedro",
        "San Roque",
        "San Vicente",
        "Santa Cruz",
        "Santo Nino (Pob.)",
        "Sindaton",
        "Southern Davao",
        "Tagpore",
        "Tibungol",
        "Upper Licanan",
        "Waterfall",
    ],
    "Island Garden City of Samal": [
        "Adecor",
        "Anonang",
        "Aumbay",
        "Aundanao",
        "Balet",
        "Bandera",
        "Caliclic",
        "Camudmud",
        "Catagman",
        "Cawag",
        "Cogon",
        "Dadatan",
        "Del Monte",
        "Guilon",
        "Kanaan",
        "Kinawitnon",
        "Libertad",
        "Libuak",
        "Licup",
        "Limao",
        "Linosutan",
        "Mambago-A",
        "Mambago-B",
        "Miranda (Pob.)",
        "Moncado (Pob.)",
        "Pangubatan",
        "Penaplata (Pob.)",
        "Poblacion",
        "San Agustin",
        "San Antonio",
        "San Isidro",
        "San Jose",
        "San Miguel",
        "San Remigio",
        "Santa Cruz",
        "Santo Nino",
        "Sion",
        "Tagbaobo",
        "Tagbay",
        "Tagbitan-ag",
        "Tagdaliao",
        "Tagpopongan",
        "Tambo",
        "Toril",
    ],
    "Santo Tomas": [
        "Balagunan",
        "Bobongon",
        "Casig-Ang",
        "Esperanza",
        "Kimamon",
        "Kinamayan",
        "La Libertad",
        "Lungaog",
        "Magwawa",
        "New Katipunan",
        "New Visayas",
        "Pantaron",
        "Salvacion",
        "San Jose",
        "San Miguel",
        "San Vicente",
        "Talomo",
        "Tibal-og (Pob.)",
        "Tulalian",
    ],
    "City of Tagum": [
        "Apokon",
        "Bincungan",
        "Busaon",
        "Canocotan",
        "Cuambogan",
        "La Filipina",
        "Liboganon",
        "Madaum",
        "Magdum",
        "Magugpo East",
        "Magugpo North",
        "Magugpo Poblacion",
        "Magugpo South",
        "Magugpo West",
        "Mankilam",
        "New Balamban",
        "Nueva Fuerza",
        "Pagsabangan",
        "Pandapan",
        "San Agustin",
        "San Isidro",
        "San Miguel",
        "Visayan Village",
    ],
    "Talaingod": [
        "Dagohoy",
        "Palma Gil",
        "Santo Nino",
    ],
    "Braulio E. Dujali": [
        "Cabayangan",
        "Dujali",
        "Magupising",
        "New Casay",
        "Tanglaw",
    ],
    "San Isidro": [
        "Dacudao",
        "Datu Balong",
        "Igangon",
        "Kipalili",
        "Libuton",
        "Linao",
        "Mamangan",
        "Monte Dujali",
        "Pinamuno",
        "Sabangan",
        "San Miguel",
        "Santo Nino",
        "Sawata",
    ],
};

const LOCATION_STAGE = {
    province: "province",
    city: "city",
    barangay: "barangay",
};

const LOCATION_ACTIONS = {
    backProvince: "__back_province",
    backCity: "__back_city",
    currentLocation: "__current_location",
};

const resetSelectOptions = (selectElement, placeholder) => {
    if (!selectElement) {
        return;
    }

    selectElement.innerHTML = "";
    const option = document.createElement("option");
    option.value = "";
    option.textContent = placeholder;
    option.disabled = true;
    option.selected = true;
    selectElement.appendChild(option);
};

const appendSelectOption = (selectElement, value, label) => {
    if (!selectElement) {
        return;
    }

    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    selectElement.appendChild(option);
};

const populateSelectOptions = (selectElement, options, placeholder, selectedValue = "") => {
    if (!selectElement) {
        return;
    }

    resetSelectOptions(selectElement, placeholder);
    options.forEach((optionValue) => {
        appendSelectOption(selectElement, optionValue, optionValue);
    });

    if (selectedValue) {
        selectElement.value = selectedValue;
    }
};

const createLocationState = ({ hiddenInput, select, summary }) => {
    return {
        hiddenInput,
        select,
        summary,
        stage: LOCATION_STAGE.province,
        selectedProvince: "",
        selectedCity: "",
        selectedBarangay: "",
        legacyValue: "",
    };
};

const renderLocationSummary = (state) => {
    if (!state || !state.summary) {
        return;
    }

    const parts = state.legacyValue
        ? [state.legacyValue]
        : [state.selectedProvince, state.selectedCity, state.selectedBarangay].filter(Boolean);
    if (!parts.length) {
        state.summary.textContent = "";
        state.summary.hidden = true;
        return;
    }

    state.summary.textContent = parts.join(", ");
    state.summary.hidden = false;
};

const updateLocationHiddenValue = (state) => {
    if (!state || !state.hiddenInput) {
        return;
    }

    if (state.legacyValue) {
        state.hiddenInput.value = state.legacyValue;
        return;
    }

    const province = state.selectedProvince;
    if (!province) {
        state.hiddenInput.value = "";
        return;
    }

    if (province !== DAVAO_DEL_NORTE_PROVINCE) {
        state.hiddenInput.value = province;
        return;
    }

    if (!state.selectedCity || !state.selectedBarangay) {
        state.hiddenInput.value = "";
        return;
    }

    state.hiddenInput.value = `${province}, ${state.selectedCity}, ${state.selectedBarangay}`;
};

const renderLocationSelect = (state) => {
    if (!state || !state.select) {
        return;
    }

    if (state.stage === LOCATION_STAGE.province) {
        populateSelectOptions(state.select, DAVAO_REGION_PROVINCES, "Select province", state.selectedProvince);
        if (state.legacyValue) {
            appendSelectOption(
                state.select,
                LOCATION_ACTIONS.currentLocation,
                `Current: ${state.legacyValue}`,
            );
            state.select.value = LOCATION_ACTIONS.currentLocation;
        }
        state.select.setAttribute("aria-label", "Select province");
        return;
    }

    if (state.stage === LOCATION_STAGE.city) {
        resetSelectOptions(state.select, "Select city/municipality");
        appendSelectOption(state.select, LOCATION_ACTIONS.backProvince, "Change province");

        const cities = Object.keys(DAVAO_DEL_NORTE_LOCATIONS).sort();
        cities.forEach((city) => {
            appendSelectOption(state.select, city, city);
        });

        if (state.selectedCity) {
            state.select.value = state.selectedCity;
        }
        state.select.setAttribute("aria-label", "Select city or municipality");
        return;
    }

    resetSelectOptions(state.select, "Select barangay");
    appendSelectOption(state.select, LOCATION_ACTIONS.backCity, "Change city/municipality");

    const barangays = state.selectedCity ? (DAVAO_DEL_NORTE_LOCATIONS[state.selectedCity] || []) : [];
    barangays.forEach((barangay) => {
        appendSelectOption(state.select, barangay, barangay);
    });

    if (state.selectedBarangay) {
        state.select.value = state.selectedBarangay;
    }
    state.select.setAttribute("aria-label", "Select barangay");
};

const handleLocationSelectChange = (state) => {
    if (!state || !state.select) {
        return;
    }

    const value = state.select.value;
    if (state.stage === LOCATION_STAGE.province) {
        if (value === LOCATION_ACTIONS.currentLocation) {
            updateLocationHiddenValue(state);
            renderLocationSummary(state);
            return;
        }

        state.legacyValue = "";
        state.selectedProvince = value;
        state.selectedCity = "";
        state.selectedBarangay = "";

        if (!value) {
            renderLocationSelect(state);
            updateLocationHiddenValue(state);
            renderLocationSummary(state);
            return;
        }

        if (value === DAVAO_DEL_NORTE_PROVINCE) {
            state.stage = LOCATION_STAGE.city;
        } else {
            state.stage = LOCATION_STAGE.province;
        }
    } else if (state.stage === LOCATION_STAGE.city) {
        if (value === LOCATION_ACTIONS.backProvince) {
            state.stage = LOCATION_STAGE.province;
            state.selectedProvince = "";
            state.selectedCity = "";
            state.selectedBarangay = "";
        } else if (value) {
            state.selectedCity = value;
            state.selectedBarangay = "";
            state.stage = LOCATION_STAGE.barangay;
        }
    } else if (state.stage === LOCATION_STAGE.barangay) {
        if (value === LOCATION_ACTIONS.backCity) {
            state.stage = LOCATION_STAGE.city;
            state.selectedBarangay = "";
        } else if (value) {
            state.selectedBarangay = value;
        }
    }

    renderLocationSelect(state);
    updateLocationHiddenValue(state);
    renderLocationSummary(state);
};

const bindLocationControls = (state) => {
    if (!state || !state.select || !state.hiddenInput) {
        return;
    }

    state.select.required = true;
    state.select.addEventListener("change", () => {
        handleLocationSelectChange(state);
    });

    resetLocationState(state);
};

const resolveLocationParts = (locationValue) => {
    const parts = String(locationValue || "")
        .split(",")
        .map((part) => part.trim())
        .filter(Boolean);

    if (!parts.length) {
        return { province: "", city: "", barangay: "" };
    }

    const provinceIndex = parts.findIndex((part) => DAVAO_REGION_PROVINCES.includes(part));
    if (provinceIndex === -1) {
        return {
            province: parts[0] || "",
            city: parts[1] || "",
            barangay: parts[2] || "",
        };
    }

    const province = parts[provinceIndex];
    const remaining = parts.filter((_, index) => index !== provinceIndex);
    if (provinceIndex === 2 && remaining.length === 2) {
        return {
            province,
            city: remaining[1] || "",
            barangay: remaining[0] || "",
        };
    }

    return {
        province,
        city: remaining[0] || "",
        barangay: remaining[1] || "",
    };
};

const resetLocationState = (state) => {
    if (!state) {
        return;
    }

    state.stage = LOCATION_STAGE.province;
    state.selectedProvince = "";
    state.selectedCity = "";
    state.selectedBarangay = "";
    state.legacyValue = "";
    renderLocationSelect(state);
    updateLocationHiddenValue(state);
    renderLocationSummary(state);
};

const applyLocationSelection = (state, locationValue) => {
    if (!state) {
        return;
    }

    const rawLocation = String(locationValue || "").trim();
    const resolved = resolveLocationParts(rawLocation);
    const isKnownProvince = DAVAO_REGION_PROVINCES.includes(resolved.province);
    const isCompleteDavaoDelNorte = resolved.province === DAVAO_DEL_NORTE_PROVINCE
        && Boolean(resolved.city)
        && Boolean(resolved.barangay)
        && Array.isArray(DAVAO_DEL_NORTE_LOCATIONS[resolved.city])
        && DAVAO_DEL_NORTE_LOCATIONS[resolved.city].includes(resolved.barangay);
    const isSupportedSelection = !rawLocation
        || (
            isKnownProvince
            && resolved.province !== DAVAO_DEL_NORTE_PROVINCE
            && rawLocation === resolved.province
        )
        || isCompleteDavaoDelNorte;

    state.legacyValue = isSupportedSelection ? "" : rawLocation;
    state.selectedProvince = resolved.province;
    state.selectedCity = resolved.city;
    state.selectedBarangay = resolved.barangay;

    if (state.legacyValue || !state.selectedProvince) {
        state.stage = LOCATION_STAGE.province;
    } else if (state.selectedProvince !== DAVAO_DEL_NORTE_PROVINCE) {
        state.stage = LOCATION_STAGE.province;
    } else if (state.selectedCity && state.selectedBarangay) {
        state.stage = LOCATION_STAGE.barangay;
    } else if (state.selectedCity) {
        state.stage = LOCATION_STAGE.city;
    } else {
        state.stage = LOCATION_STAGE.province;
    }

    renderLocationSelect(state);
    updateLocationHiddenValue(state);
    renderLocationSummary(state);
};

const syncLocationState = (state) => {
    if (!state) {
        return;
    }
    updateLocationHiddenValue(state);
    renderLocationSummary(state);
};

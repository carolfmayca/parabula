const VIA_LABELS = {
    oral: "Oral",
    intravenosa: "Intravenosa (IV)",
    intramuscular: "Intramuscular (IM)",
    subcutanea: "Subcutânea (SC)",
    topica: "Tópica",
    inalatoria: "Inalatória",
    oftalmica: "Oftálmica",
    nasal: "Nasal",
    retal: "Retal",
};

let medicamentosList = [];

function getViaLabel(via) {
    return VIA_LABELS[via] || via;
}

function normalizeMedicamento(item) {
    if (typeof item === "string") {
        return { name: item, via: null, dose: null };
    }

    return {
        name: item.name,
        via: item.via || null,
        dose: item.dose || null
    };
}

document.addEventListener("DOMContentLoaded", function() {
    const addMedicineBtn = document.getElementById("add-medicine-btn");
    const novoMedicamentoInput = document.getElementById("novo-medicamento");
    const medicamentoViaSelect = document.getElementById("medicamento-via");
    const medicamentoDoseInput = document.getElementById("medicamento-dose");
    const medicamentosList_element = document.getElementById("medicamentos-list");
    const formulario = document.querySelector("form");

    function updateViaSelectStyle() {
        medicamentoViaSelect.classList.toggle("is-placeholder", !medicamentoViaSelect.value);
    }

    medicamentoViaSelect.addEventListener("change", updateViaSelectStyle);
    updateViaSelectStyle();

    document.querySelectorAll(".medicine-item").forEach((item) => {
        const name = item.dataset.name;
        if (!name) {
            return;
        }

        medicamentosList.push({
            name,
            via: item.dataset.via || null,
            dose: item.dataset.dose || null
        });
    });

    addMedicineBtn.addEventListener("click", function() {
        const medicName = novoMedicamentoInput.value.trim();
        const selectedVia = medicamentoViaSelect.value || null;
        const dose = medicamentoDoseInput.value.trim() || null;

        if (!medicName) {
            alert("Digite o nome do medicamento");
            return;
        }

        medicamentosList.push({
            name: medicName,
            via: selectedVia,
            dose: dose
        });

        novoMedicamentoInput.value = "";
        medicamentoViaSelect.value = "";
        medicamentoDoseInput.value = "";
        updateViaSelectStyle();
        renderMedicamentos();
    });

    novoMedicamentoInput.addEventListener("keypress", function(e) {
        if (e.key === "Enter") {
            e.preventDefault();
            addMedicineBtn.click();
        }
    });

    document.addEventListener("click", function(e) {
        if (e.target.classList.contains("remove-medicine")) {
            const index = e.target.dataset.index;
            medicamentosList.splice(index, 1);
            renderMedicamentos();
        }
    });

    const sexInputs = document.querySelectorAll('input[name="biological_sex"]');
    const pregnancyInputs = document.querySelectorAll('input[name="is_pregnant"]');

    function updatePregnancyState() {
        const selectedSex = document.querySelector('input[name="biological_sex"]:checked');
        const shouldEnable = selectedSex && selectedSex.value !== "male";

        pregnancyInputs.forEach((input) => {
            input.disabled = !shouldEnable;
            if (!shouldEnable) {
                input.checked = false;
            }
        });

        pregnancyInputs.forEach((input) => {
            const label = input.closest("label");
            if (label) {
                if (!shouldEnable) {
                    label.classList.add("disabled");
                } else {
                    label.classList.remove("disabled");
                }
            }
        });
    }

    sexInputs.forEach((input) => {
        input.addEventListener("change", updatePregnancyState);
    });

    updatePregnancyState();

    formulario.addEventListener("submit", function(e) {
        e.preventDefault();

        if (medicamentosList.length < 2) {
            alert("Informe pelo menos 2 medicamentos");
            return;
        }

        formulario.querySelectorAll('input[type="hidden"][name="medicamentos"]').forEach((el) => el.remove());

        medicamentosList.forEach((med) => {
            const hidden = document.createElement("input");
            hidden.type = "hidden";
            hidden.name = "medicamentos";
            hidden.value = JSON.stringify({
                name: med.name,
                via: med.via,
                dose: med.dose
            });
            formulario.appendChild(hidden);
        });

        formulario.submit();
    });

    function renderMedicamentos() {
        medicamentosList_element.innerHTML = "";

        medicamentosList.forEach((med, index) => {
            const normalized = normalizeMedicamento(med);
            const div = document.createElement("div");
            div.className = "medicine-item";

            const viaHtml = normalized.via
                ? `<span class="medicine-item-via">Via: ${getViaLabel(normalized.via)}</span>`
                : "";
            
            const doseHtml = normalized.dose
            ? `<span class="medicine-item-dose">Dosagem: ${normalized.dose}</span>`
            : "";

            div.innerHTML = `
                <div class="medicine-item-content">
                    <span class="medicine-item-name">${normalized.name}</span>
                    ${viaHtml}
                    ${doseHtml}
                </div>
                <button type="button" class="remove-medicine" data-index="${index}">×</button>
            `;
            medicamentosList_element.appendChild(div);
        });
    }

    renderMedicamentos();
});
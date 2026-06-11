// Gerenciar lista de medicamentos
let medicamentosList = [];

document.addEventListener("DOMContentLoaded", function() {
    const addMedicineBtn = document.getElementById("add-medicine-btn");
    const novoMedicamentoInput = document.getElementById("novo-medicamento");
    const medicamentosList_element = document.getElementById("medicamentos-list");
    const formulario = document.querySelector("form");

    // Carregar medicamentos iniciais da view
    const initialItems = document.querySelectorAll(".medicine-item");
    initialItems.forEach(item => {
        const medicName = item.querySelector("span").textContent;
        if (medicName) {
            medicamentosList.push(medicName);
        }
    });

    // Adicionar medicamento
    addMedicineBtn.addEventListener("click", function() {
        const medicName = novoMedicamentoInput.value.trim();

        if (!medicName) {
            alert("Digite o nome do medicamento");
            return;
        }

        medicamentosList.push(medicName);
        novoMedicamentoInput.value = "";
        renderMedicamentos();
    });

    // Permitir adicionar com Enter
    novoMedicamentoInput.addEventListener("keypress", function(e) {
        if (e.key === "Enter") {
            addMedicineBtn.click();
        }
    });

    // Remover medicamento
    document.addEventListener("click", function(e) {
        if (e.target.classList.contains("remove-medicine")) {
            const index = e.target.dataset.index;
            medicamentosList.splice(index, 1);
            renderMedicamentos();
        }
    });

    const sexInputs = document.querySelectorAll('input[name="biological_sex"]');
    const pregnancyInputs = document.querySelectorAll('input[name="is_pregnant"]');
    const pregnancyLabels = document.querySelectorAll('input[name="is_pregnant"]');

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
            const label = input.closest('label');
            if (label) {
                if (!shouldEnable) {
                    label.classList.add('disabled');
                } else {
                    label.classList.remove('disabled');
                }
            }
        });
    }

    sexInputs.forEach((input) => {
        input.addEventListener('change', updatePregnancyState);
    });

    updatePregnancyState();

    // Validar e enviar formulário
    formulario.addEventListener("submit", function(e) {
        e.preventDefault();

        if (medicamentosList.length < 2) {
            alert("Informe pelo menos 2 medicamentos");
            return;
        }

        // Limpa campos hidden antigos para evitar duplicação em múltiplos submits.
        formulario.querySelectorAll('input[type="hidden"][name="medicamentos"]').forEach((el) => el.remove());

        // Serializa a lista dinâmica de medicamentos para o POST do formulário.
        medicamentosList.forEach((med) => {
            const hidden = document.createElement("input");
            hidden.type = "hidden";
            hidden.name = "medicamentos";
            hidden.value = med;
            formulario.appendChild(hidden);
        });

        // Enviar formulário normalmente (via POST)
        formulario.submit();
    });

    function renderMedicamentos() {
        medicamentosList_element.innerHTML = "";

        medicamentosList.forEach((med, index) => {
            const div = document.createElement("div");
            div.className = "medicine-item";
            div.innerHTML = `
                <span>${med}</span>
                <button type="button" class="remove-medicine" data-index="${index}">×</button>
            `;
            medicamentosList_element.appendChild(div);
        });
    }

    // Render inicial
    renderMedicamentos();
});

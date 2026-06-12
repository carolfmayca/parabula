exports.index = (req, res) => {

    res.render("interaction", {
        medicamentos: []
    });

};

exports.results = async (req, res) => {
    try {
        // Capturar dados do formulário
        const { medicamentos, idade, biological_sex, is_pregnant, comorbidades } = req.body;

        const meds = Array.isArray(medicamentos)
            ? medicamentos.filter(Boolean)
            : (medicamentos ? [medicamentos] : []);

        // Validar dados
        if (meds.length < 2) {
            return res.status(400).render("interaction", {
                medicamentos: meds,
                erro: "Informe pelo menos 2 medicamentos"
            });
        }

        // Preparar payload para a API
        const payload = {
            drugs: meds,
            patient: {
                age: parseInt(idade) || 0,
                biological_sex: biological_sex || "other",
                is_pregnant: is_pregnant === "true",
                comorbidities: comorbidades
                    ? comorbidades.split(",").map(c => c.trim()).filter(c => c)
                    : []
            }
        };

        const backendBaseUrl = (process.env.BACKEND_URL || "http://localhost:8000").replace(/\/$/, "");

        // Chamar API backend
        const response = await fetch(`${backendBaseUrl}/drug-interactions/check`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }

        const apiResponse = await response.json();

        // Passar dados para a view de resultados
        res.render("results", {
            drugs: payload.drugs,
            patient: payload.patient,
            apiResponse: apiResponse
        });

    } catch (error) {
        console.error("Erro ao analisar interações:", error);
        res.status(500).render("interaction", {
            medicamentos: req.body.medicamentos || [],
            erro: "Erro ao analisar interações. Tente novamente."
        });
    }
};
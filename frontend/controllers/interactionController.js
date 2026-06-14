function parseMedicamentos(rawMedicamentos) {
    const items = Array.isArray(rawMedicamentos)
        ? rawMedicamentos.filter(Boolean)
        : (rawMedicamentos ? [rawMedicamentos] : []);

    return items.map((item) => {
        if (typeof item === "string") {
            try {
                const parsed = JSON.parse(item);
                if (parsed && parsed.name) {
                    return {
                        name: parsed.name,
                        via: parsed.via || null
                    };
                }
            } catch (_) {
                return { name: item, via: null };
            }
        }

        if (item && item.name) {
            return {
                name: item.name,
                via: item.via || null
            };
        }

        return { name: String(item), via: null };
    });
}

exports.index = (req, res) => {
    res.render("interaction", {
        medicamentos: []
    });
};

exports.results = async (req, res) => {
    try {
        const { medicamentos, idade, biological_sex, is_pregnant, comorbidades } = req.body;
        const meds = parseMedicamentos(medicamentos);

        if (meds.length < 2) {
            return res.status(400).render("interaction", {
                medicamentos: meds,
                erro: "Informe pelo menos 2 medicamentos"
            });
        }

        const parsedAge = idade !== undefined && idade !== "" ? parseInt(idade, 10) : null;
        const payload = {
            drugs: meds.map((med) => ({
                name: med.name,
                via: med.via
            })),
            patient: {
                age: Number.isNaN(parsedAge) ? null : parsedAge,
                biological_sex: biological_sex || null,
                is_pregnant: is_pregnant === "true"
                    ? true
                    : is_pregnant === "false"
                        ? false
                        : null,
                comorbidities: comorbidades
                    ? comorbidades.split(",").map(c => c.trim()).filter(c => c)
                    : null
            }
        };

        const backendBaseUrl = (process.env.BACKEND_URL || "http://localhost:8000").replace(/\/$/, "");

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

        res.render("results", {
            drugs: payload.drugs,
            patient: payload.patient,
            apiResponse: apiResponse
        });

    } catch (error) {
        console.error("Erro ao analisar interações:", error);
        res.status(500).render("interaction", {
            medicamentos: parseMedicamentos(req.body.medicamentos),
            erro: "Erro ao analisar interações. Tente novamente."
        });
    }
};
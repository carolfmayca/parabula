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
                        via: parsed.via || null,
                        dose: parsed.dose || null
                    };
                }
            } catch (_) {
                return { name: item, via: null, dose: null };
            }
        }

        if (item && item.name) {
            return {
                name: item.name,
                via: item.via || null,
                dose: item.dose || null
            };
        }

        return { name: String(item), via: null, dose: null };
    });
}

function extractApiErrorMessage(errorBody) {
    try {
        const parsed = JSON.parse(errorBody);
        const detail = parsed.detail;

        if (Array.isArray(detail) && detail.length > 0) {
            return detail
                .map((item) => item.msg || item.message)
                .filter(Boolean)
                .join(" ");
        }

        if (detail && typeof detail === "object") {
            return detail.message || detail.msg || "Não foi possível validar os dados informados.";
        }

        if (typeof detail === "string") {
            return detail;
        }
    } catch (_) {
        return null;
    }

    return null;
}

exports.landing = (req, res) => {
    res.render("landing");
};

exports.team = (req, res) => {
    res.render("team");
};

exports.index = (req, res) => {
    res.render("interaction", {
        medicamentos: []
    });
};

exports.results = async (req, res) => {
    try {
        const { medicamentos, idade, biological_sex, is_pregnant, comorbidades, peso } = req.body;
        const meds = parseMedicamentos(medicamentos);
        const parsedAge = idade !== undefined && idade !== "" ? parseInt(idade, 10) : null;
        let weight = null;
        if (peso !== undefined && peso !== "") {
            const pesoNum = parseFloat(String(peso).replace(",", "."));
            if (!Number.isNaN(pesoNum)) {
                const kg = Math.floor(pesoNum);
                const g = Math.round((pesoNum - kg) * 1000);
                weight = [kg, g];
            }
        }
        const hasPatientData = Boolean(
            parsedAge !== null ||
            weight !== null ||
            biological_sex ||
            is_pregnant ||
            (comorbidades && comorbidades.trim())
        );

        if (meds.length === 0) {
            return res.status(400).render("interaction", {
                medicamentos: meds,
                erro: "Informe pelo menos 1 medicamento."
            });
        }

        if (meds.length === 1 && !hasPatientData) {
            return res.status(400).render("interaction", {
                medicamentos: meds,
                erro: "Com 1 medicamento, informe ao menos um dado do paciente."
            });
        }

        const payload = {
            drugs: meds.map((med) => ({
                name: med.name,
                via: med.via,
                dose: med.dose
            })),
            patient: {
                age: Number.isNaN(parsedAge) ? null : parsedAge,
                weight: weight,
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
        const apiAuthToken = process.env.API_AUTH_TOKEN || "pb_frontend_demo_token";
        
        console.log(`${backendBaseUrl}/drug-interactions/check`);
        
        const response = await fetch(`${backendBaseUrl}/drug-interactions/check`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${apiAuthToken}`
            },
            body: JSON.stringify(payload)
        });
        
        if (!response.ok) {
            const errorBody = await response.text();
            console.error("Detalhe do erro:", errorBody);
            return res.status(response.status).render("interaction", {
                medicamentos: meds,
                erro: extractApiErrorMessage(errorBody)
                    || "Não foi possível validar os dados informados."
            });
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

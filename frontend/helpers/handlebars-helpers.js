function normalizeSeverity(value) {
    if (!value) return null;

    const normalized = String(value).trim().toLowerCase();
    if (normalized === 'alta' || normalized === 'high') return 'high';
    if (normalized === 'baixa' || normalized === 'low') return 'low';
    if (normalized === 'média' || normalized === 'media' || normalized === 'medium') return 'medium';
    return null;
}

function getHighestSeverityFromItems(items) {
    if (!Array.isArray(items) || !items.length) return 'low';

    const hasHigh = items.some(item => normalizeSeverity(item && item.severity) === 'high');
    if (hasHigh) return 'high';

    const hasMedium = items.some(item => normalizeSeverity(item && item.severity) === 'medium');
    if (hasMedium) return 'medium';

    return 'low';
}

function resolveRiskSeverity(clinicalRisks) {
    const direct = normalizeSeverity(clinicalRisks && clinicalRisks.severity);
    if (direct) return direct;

    return getHighestSeverityFromItems(clinicalRisks && clinicalRisks.items);
}

module.exports = {
    eq: function(a, b) {
        return a === b;
    },
    
    upper: function(str) {
        if (!str) return '';
        return str.toUpperCase();
    },
    
    join: function(arr, separator, options) {
        if (!arr) return '';
        return arr.join(separator || ', ');
    },
    
    countSeverity: function(severity, details) {
        if (!details || !Array.isArray(details)) return 0;
        return details.filter(d => d.severity === severity).length;
    },

    severityClass: function(severity) {
        return normalizeSeverity(severity) || 'medium';
    },

    severityLabel: function(severity) {
        const normalized = normalizeSeverity(severity);

        if (normalized === 'high') return 'ALTO';
        if (normalized === 'low') return 'BAIXO';
        return 'MÉDIO';
    },

    severityText: function(severity) {
        const normalized = normalizeSeverity(severity);

        if (normalized === 'high') return 'Alta';
        if (normalized === 'low') return 'Baixa';
        return 'Média';
    },

    riskSeverityClass: function(clinicalRisks) {
        return resolveRiskSeverity(clinicalRisks);
    },

    riskSeverityLabel: function(clinicalRisks) {
        const severity = resolveRiskSeverity(clinicalRisks);
        if (severity === 'high') return 'ALTO';
        if (severity === 'low') return 'BAIXO';
        return 'MÉDIO';
    },

    capitalizeFirst: function(text) {
        if (!text) return '';

        const value = String(text).trim();
        if (!value) return '';

        return value.charAt(0).toUpperCase() + value.slice(1).toLowerCase();
    },

    joinCapitalized: function(arr, separator) {
        if (!arr || !Array.isArray(arr)) return '';
        return arr
            .map(item => {
                const s = String(item).trim();
                return s ? s.charAt(0).toUpperCase() + s.slice(1) : '';
            })
            .filter(Boolean)
            .join(separator || ', ');
    },

    truncate: function(text, maxLength) {
        if (!text) return '';

        const value = String(text).trim();
        const limit = Number(maxLength) || 140;

        if (value.length <= limit) return value;
        return value.slice(0, limit).trimEnd() + '...';
    },

    ptSex: function(biologicalSex) {
        if (biologicalSex === null || biologicalSex === undefined || biologicalSex === '') {
            return 'Não informado';
        }
        if (biologicalSex === 'female') return 'Feminino';
        if (biologicalSex === 'male') return 'Masculino';
        if (biologicalSex === 'other') return 'Outro';
        return 'Não informado';
    },

    ptAge: function(age) {
        if (age === null || age === undefined || age === '') {
            return 'Não informado';
        }
        return `${age} anos`;
    },

    ptPregnant: function(isPregnant) {
        if (isPregnant === null || isPregnant === undefined || isPregnant === '') {
            return 'Não informado';
        }
        if (isPregnant === true || isPregnant === 'true') return 'Sim';
        if (isPregnant === false || isPregnant === 'false') return 'Não';
        return 'Não informado';
    },

    ptComorbidities: function(comorbidities) {
        if (!comorbidities || !Array.isArray(comorbidities) || !comorbidities.length) {
            return 'Não informado';
        }

        return comorbidities
            .map(item => {
                const s = String(item).trim();
                return s ? s.charAt(0).toUpperCase() + s.slice(1) : '';
            })
            .filter(Boolean)
            .join(', ');
    },

    ptVia: function(via) {
        const labels = {
            oral: 'Oral',
            intravenosa: 'Intravenosa (IV)',
            intramuscular: 'Intramuscular (IM)',
            subcutanea: 'Subcutânea (SC)',
            topica: 'Tópica',
            inalatoria: 'Inalatória',
            oftalmica: 'Oftálmica',
            nasal: 'Nasal',
            retal: 'Retal',
            outra: 'Outra'
        };

        if (!via) return '';
        return labels[via] || via;
    }
};

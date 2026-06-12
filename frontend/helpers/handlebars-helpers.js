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
        if (!severity) return 'medium';

        const normalized = String(severity).trim().toLowerCase();

        if (normalized === 'alta' || normalized === 'high') return 'high';
        if (normalized === 'baixa' || normalized === 'low') return 'low';
        return 'medium';
    },

    severityLabel: function(severity) {
        const normalized = String(severity || '').trim().toLowerCase();

        if (normalized === 'alta' || normalized === 'high') return 'ALTO';
        if (normalized === 'baixa' || normalized === 'low') return 'BAIXO';
        return 'MÉDIO';
    },

    severityText: function(severity) {
        const normalized = String(severity || '').trim().toLowerCase();

        if (normalized === 'alta' || normalized === 'high') return 'Alta';
        if (normalized === 'baixa' || normalized === 'low') return 'Baixa';
        return 'Média';
    },

    capitalizeFirst: function(text) {
        if (!text) return '';

        const value = String(text).trim();
        if (!value) return '';

        return value.charAt(0).toUpperCase() + value.slice(1).toLowerCase();
    },

    ptSex: function(biologicalSex) {
        if (biologicalSex === 'female') return 'Feminino';
        if (biologicalSex === 'male') return 'Masculino';
        return 'Outro';
    }
};

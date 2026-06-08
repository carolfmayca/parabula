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
    }
};

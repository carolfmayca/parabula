exports.index = (req, res) => {

    res.render("interaction", {
        medicamentos: [
            "Claritromicina",
            "Claritromicina"
        ]
    });

};

exports.results = (req, res) => {
    res.render("results");
};
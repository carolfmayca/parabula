exports.index = (req, res) => {

    res.render("interaction", {
        medicamentos: [
            "Claritromicina",
            "Claritromicina"
        ]
    });

};
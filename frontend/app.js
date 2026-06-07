const express = require("express");
const { engine } = require("express-handlebars");

const app = express();

app.engine("hbs", engine({
    extname: ".hbs"
}));

app.set("view engine", "hbs");
app.set("views", "./views");

app.use(express.static("public"));
app.use(express.urlencoded({ extended: true }));

const routes = require("./routes");
app.use("/", routes);

app.listen(3000, () => {
    console.log("Servidor rodando em http://localhost:3000");
});
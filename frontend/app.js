const express = require("express");
const { engine } = require("express-handlebars");
const fs = require("fs");
const path = require("path");
const helpers = require("./helpers/handlebars-helpers");

function loadEnvFile() {
    const envPath = path.join(__dirname, ".env");
    if (!fs.existsSync(envPath)) {
        return;
    }

    const envFile = fs.readFileSync(envPath, "utf-8");
    envFile.split(/\r?\n/).forEach((line) => {
        const trimmed = line.trim();
        if (!trimmed || trimmed.startsWith("#")) {
            return;
        }

        const separatorIndex = trimmed.indexOf("=");
        if (separatorIndex === -1) {
            return;
        }

        const key = trimmed.slice(0, separatorIndex).trim();
        const value = trimmed.slice(separatorIndex + 1).trim();
        if (key && process.env[key] === undefined) {
            process.env[key] = value.replace(/^["']|["']$/g, "");
        }
    });
}

loadEnvFile();

const app = express();

app.engine("hbs", engine({
    extname: ".hbs",
    helpers: helpers
}));

app.set("view engine", "hbs");
app.set("views", "./views");

app.use(express.static("public"));
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

const routes = require("./routes");
app.use("/", routes);

app.listen(3000, () => {
    console.log("Servidor rodando em http://localhost:3000");
});

const express = require("express");
const router = express.Router();

const interactionController = require("../controllers/interactionController");

router.get("/", interactionController.landing);
router.get("/equipe", interactionController.team);
router.post("/results", interactionController.results);
router.get("/interagir", interactionController.index);


module.exports = router;
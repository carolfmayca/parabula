const express = require("express");
const router = express.Router();

const interactionController = require("../controllers/interactionController");

router.get("/", interactionController.index);
router.post("/results", interactionController.results);

module.exports = router;
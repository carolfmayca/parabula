const express = require("express");
const router = express.Router();

const interactionController = require("../controllers/interactionController");

router.get("/", interactionController.index);

module.exports = router;
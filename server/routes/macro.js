const express = require("express");
const router = express.Router();
const { getMacro } = require("../controllers/macroController");

router.get("/", getMacro);

module.exports = router;

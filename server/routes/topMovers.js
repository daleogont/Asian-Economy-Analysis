const express = require('express');
const router = express.Router();
const { getTopMovers } = require('../controllers/topMoversController');

router.get('/', getTopMovers);

module.exports = router;

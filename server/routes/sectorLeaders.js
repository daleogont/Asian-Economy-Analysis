const express = require('express');
const router = express.Router();
const { getSectorLeaders } = require('../controllers/sectorLeadersController');

router.get('/', getSectorLeaders);

module.exports = router;

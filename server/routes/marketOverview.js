const express = require('express');
const router = express.Router();
const { getMarketOverview } = require('../controllers/marketOverviewController');

router.get('/', getMarketOverview);

module.exports = router;

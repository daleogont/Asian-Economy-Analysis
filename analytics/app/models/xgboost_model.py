from xgboost import XGBRegressor

from app.models.lagged_base import LaggedFeatureModel


class XgboostModel(LaggedFeatureModel):
    """XGBoost prototype — price-only lagged features (lags 1,2,3,5,10,20 + time index).

    Full multi-feature version (+ macro, fundamentals) is Stage 3 scope.
    """

    name = "xgboost"

    def _build_estimator(self):
        return XGBRegressor(n_estimators=100, learning_rate=0.1, random_state=42)

from sklearn.ensemble import RandomForestRegressor

from app.models.lagged_base import LaggedFeatureModel


class RandomForestModel(LaggedFeatureModel):
    """Random Forest on lagged close prices (lags 1,2,3,5,10,20 + time index)."""

    name = "random_forest"

    def _build_estimator(self):
        return RandomForestRegressor(n_estimators=100, random_state=42)

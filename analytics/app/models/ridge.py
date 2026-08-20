from sklearn.linear_model import Ridge

from app.models.lagged_base import LaggedFeatureModel


class RidgeModel(LaggedFeatureModel):
    """Ridge regression on lagged close prices (lags 1,2,3,5,10,20 + time index)."""

    name = "ridge"

    def _build_estimator(self):
        return Ridge()

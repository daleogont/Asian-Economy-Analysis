import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.preprocessing import MinMaxScaler

from app.models.base import BaseForecastModel

SEQUENCE_LENGTH   = 60
HIDDEN_SIZE       = 64
NUM_LAYERS        = 2
DROPOUT           = 0.2
EPOCHS            = 50
BATCH_SIZE        = 32
LEARNING_RATE     = 0.001
MIN_TRAINING_ROWS = 120


class _LSTMNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=1,
            hidden_size=HIDDEN_SIZE,
            num_layers=NUM_LAYERS,
            dropout=DROPOUT,
            batch_first=True,
        )
        self.fc = nn.Linear(HIDDEN_SIZE, 1)

    def forward(self, x):
        out, _ = self.lstm(x)
        return self.fc(out[:, -1, :])  # last timestep's hidden state -> next value


def _build_sequences(values: np.ndarray, seq_len: int):
    """Sliding windows: X[i] = values[i:i+seq_len], y[i] = values[i+seq_len]."""
    X, y = [], []
    for i in range(len(values) - seq_len):
        X.append(values[i:i + seq_len])
        y.append(values[i + seq_len])
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)


class LstmModel(BaseForecastModel):
    """2-layer LSTM over MinMax-normalized close prices, 60-day lookback window.

    Unlike the lag-feature models (ridge/random_forest/xgboost), this treats
    price history as a genuine sequence rather than a flat feature vector.
    """

    name = "lstm"

    def __init__(self):
        self._model = None
        self._scaler = None
        self._last_window = None
        self._last_date = None
        self._freq = None
        self._resid_std = None

    def fit(self, series: pd.Series):
        if len(series) < MIN_TRAINING_ROWS:
            raise ValueError(
                f"LSTM needs at least {MIN_TRAINING_ROWS} rows of history, got {len(series)}"
            )

        torch.manual_seed(42)

        values = series.to_numpy(dtype=np.float32).reshape(-1, 1)
        self._scaler = MinMaxScaler(feature_range=(0, 1))
        scaled = self._scaler.fit_transform(values).flatten()

        X, y = _build_sequences(scaled, SEQUENCE_LENGTH)
        X_t = torch.from_numpy(X).unsqueeze(-1)   # (N, seq_len, 1)
        y_t = torch.from_numpy(y).unsqueeze(-1)   # (N, 1)

        self._model = _LSTMNet()
        optimizer = torch.optim.Adam(self._model.parameters(), lr=LEARNING_RATE)
        criterion = nn.MSELoss()

        self._model.train()
        n = len(X_t)
        for _ in range(EPOCHS):
            permutation = torch.randperm(n)
            for start in range(0, n, BATCH_SIZE):
                idx = permutation[start:start + BATCH_SIZE]
                batch_X, batch_y = X_t[idx], y_t[idx]

                optimizer.zero_grad()
                pred = self._model(batch_X)
                loss = criterion(pred, batch_y)
                loss.backward()
                optimizer.step()

        self._model.eval()
        with torch.no_grad():
            in_sample_pred = self._model(X_t).squeeze(-1).numpy()
        pred_prices   = self._scaler.inverse_transform(in_sample_pred.reshape(-1, 1)).flatten()
        actual_prices = self._scaler.inverse_transform(y.reshape(-1, 1)).flatten()
        self._resid_std = float(np.std(actual_prices - pred_prices))

        self._last_window = scaled[-SEQUENCE_LENGTH:].copy()
        self._last_date = series.index[-1]
        self._freq = series.index.freq or "B"
        return self

    def predict(self, steps: int) -> dict:
        window = list(self._last_window)
        preds_scaled = []

        self._model.eval()
        with torch.no_grad():
            for _ in range(steps):
                x = torch.tensor(window[-SEQUENCE_LENGTH:], dtype=torch.float32).reshape(1, SEQUENCE_LENGTH, 1)
                next_scaled = self._model(x).item()
                preds_scaled.append(next_scaled)
                window.append(next_scaled)

        mean = self._scaler.inverse_transform(np.array(preds_scaled).reshape(-1, 1)).flatten()

        future_dates = pd.date_range(self._last_date, periods=steps + 1, freq=self._freq)[1:]
        margin = 1.96 * self._resid_std
        return {
            "dates": [d.strftime("%Y-%m-%d") for d in future_dates],
            "mean":  mean.tolist(),
            "lower": (mean - margin).tolist(),
            "upper": (mean + margin).tolist(),
        }

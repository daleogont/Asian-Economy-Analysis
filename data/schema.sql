CREATE TABLE IF NOT EXISTS companies (
    ticker      VARCHAR(20) PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    country     VARCHAR(100) NOT NULL,
    sector      VARCHAR(100) NOT NULL,
    exchange    VARCHAR(50)  NOT NULL
);

CREATE TABLE IF NOT EXISTS daily_prices (
    id          SERIAL PRIMARY KEY,
    ticker      VARCHAR(20)    NOT NULL REFERENCES companies(ticker),
    date        DATE           NOT NULL,
    open        NUMERIC(18, 6),
    high        NUMERIC(18, 6),
    low         NUMERIC(18, 6),
    close       NUMERIC(18, 6) NOT NULL,
    volume      BIGINT,
    currency    VARCHAR(10)    NOT NULL DEFAULT 'USD',
    UNIQUE (ticker, date)
);

CREATE TABLE IF NOT EXISTS forecasts (
    id              SERIAL PRIMARY KEY,
    ticker          VARCHAR(20)  NOT NULL REFERENCES companies(ticker),
    forecast_date   DATE         NOT NULL,
    predicted_close NUMERIC(18, 6) NOT NULL,
    lower_bound     NUMERIC(18, 6),
    upper_bound     NUMERIC(18, 6),
    model           VARCHAR(50)  NOT NULL DEFAULT 'arima',
    created_at      TIMESTAMP    NOT NULL DEFAULT NOW(),
    UNIQUE (ticker, forecast_date, model)
);

CREATE INDEX IF NOT EXISTS idx_daily_prices_ticker      ON daily_prices (ticker);
CREATE INDEX IF NOT EXISTS idx_daily_prices_date        ON daily_prices (date);
CREATE INDEX IF NOT EXISTS idx_daily_prices_ticker_date ON daily_prices (ticker, date DESC);
CREATE INDEX IF NOT EXISTS idx_forecasts_ticker         ON forecasts (ticker);

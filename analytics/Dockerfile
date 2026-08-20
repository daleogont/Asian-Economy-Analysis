FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# The prophet wheel ships a precompiled prophet_model.bin (statically linked
# against its own bundled TBB libs, see prophet.libs/) alongside a broken,
# incomplete cmdstan-2.33.1 stub. prophet's backend init unconditionally
# points cmdstanpy at that stub if it exists, which fails validation
# ("missing makefile") even though the bundled binary doesn't need it.
# Removing the stub makes it fall through to the bundled binary directly.
RUN rm -rf "$(python -c 'import prophet, os; print(os.path.dirname(prophet.__file__))')/stan_model/cmdstan-2.33.1"

COPY app/ ./app/

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

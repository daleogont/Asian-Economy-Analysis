FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# Must happen before `pip install -r requirements.txt` and as its own index
# URL: installing the CPU-only build this way means when requirements.txt
# (which pins the same torch==2.1.2+cpu version) is processed next, pip
# sees the pin already satisfied by what's installed and never touches the
# default PyPI index for torch — which only carries the full CUDA build
# (2GB+) under that name.
RUN pip install --no-cache-dir torch==2.1.2+cpu --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt
# The prophet wheel ships a precompiled prophet_model.bin (statically linked
# against its own bundled TBB libs, see prophet.libs/) alongside a broken,
# incomplete cmdstan-2.33.1 stub. prophet's backend init unconditionally
# points cmdstanpy at that stub if it exists, which fails validation
# ("missing makefile") even though the bundled binary doesn't need it.
# Removing the stub makes it fall through to the bundled binary directly.
RUN rm -rf "$(python -c 'import prophet, os; print(os.path.dirname(prophet.__file__))')/stan_model/cmdstan-2.33.1"

COPY app/ ./app/
COPY scripts/ ./scripts/
COPY tests/ ./tests/

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

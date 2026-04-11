import os
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

DATABASE_URL = os.environ.get("DATABASE_URL", "")
engine = create_engine(DATABASE_URL, poolclass=NullPool)

def fetch_df(query: str, params: dict = None):
    import pandas as pd
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn, params=params)

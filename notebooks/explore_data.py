import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

print("=== ds_salaries.csv ===")
df1 = pd.read_csv(DATA_DIR / "ds_salaries.csv")
print(df1.shape)
print(df1.columns.tolist())
print(df1.head(3))
print(df1.dtypes)

print("\n=== ai_jobs_market_2025_2026.csv ===")
df2 = pd.read_csv(DATA_DIR / "ai_jobs_market_2025_2026.csv")
print(df2.shape)
print(df2.columns.tolist())
print(df2.head(3))
print(df2.dtypes)
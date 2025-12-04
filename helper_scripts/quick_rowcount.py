import pandas as pd

df = pd.read_parquet("yellow-cab_yellow_tripdata_2025-01.parquet")
print("Rows:", len(df))

print(df.columns)


# First file has 3.475.226 rows. 35 million in BigQuery seems reasonable :)
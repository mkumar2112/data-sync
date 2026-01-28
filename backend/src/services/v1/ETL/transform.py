import pandas as pd

class TransformService:

    def run(self, columns: list, payload: dict):
        column_names = [col.column_name for col in columns]

        df = pd.DataFrame(payload, columns=column_names)

        return df

    def _transform_by_type(self, df, columns):
        for col in columns:
            name = col["name"]
            dtype = col["type"].upper()

            if name not in df.columns:
                continue

            # DATETIME / TIMESTAMP
            if dtype in ("DATETIME", "TIMESTAMP"):
                df[name] = pd.to_datetime(
                    df[name],
                    errors="coerce"
                )

            # INT / BIGINT
            elif dtype in ("INT", "INTEGER", "BIGINT"):
                df[name] = pd.to_numeric(
                    df[name],
                    errors="coerce"
                ).astype("Int64")

            # BOOLEAN
            elif dtype in ("BOOLEAN", "BOOL"):
                df[name] = df[name].astype("boolean")

            # STRING types → no transform needed
        return df

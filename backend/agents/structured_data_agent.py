
from pathlib import Path
import re

import pandas as pd


class StructuredDataAgent:

    def __init__(self):
        self.supported_extensions = {".csv"}

    def _load_csv(self, csv_path):
        path = Path(csv_path)

        if not path.exists():
            raise FileNotFoundError(f"CSV file not found: {path}")

        if path.suffix.lower() not in self.supported_extensions:
            raise ValueError("Only CSV files are supported.")

        df = pd.read_csv(path)
        df.columns = [str(col).strip() for col in df.columns]

        if df.empty:
            raise ValueError("The CSV file contains no data rows.")

        return df

    @staticmethod
    def _normalize(value):
        return re.sub(
            r"[^a-z0-9]+",
            " ",
            str(value).lower()
        ).strip()

    def _find_column(self, question, df):
        normalized_question = self._normalize(question)

        aliases = {
            "age": ["ages"],
            "sex": ["gender"],
            "charges": ["charge", "insurance cost", "medical cost", "cost"],
            "bmi": ["body mass index"],
            "children": ["child", "number of children"],
            "smoker": ["smoking status", "smoking"],
            "region": ["area", "location"],
        }

        columns = sorted(
            df.columns,
            key=lambda col: len(self._normalize(col)),
            reverse=True,
        )

        for column in columns:
            normalized_column = self._normalize(column)

            if normalized_column and normalized_column in normalized_question:
                return column

            for alias in aliases.get(normalized_column, []):
                if alias in normalized_question:
                    return column

        return None

    def _find_category_value(self, question, df):
        normalized_question = self._normalize(question)

        category_aliases = {
            "sex": {
                "male": ["males", "man", "men"],
                "female": ["females", "woman", "women"],
            },
            "smoker": {
                "yes": ["smoker", "smokers", "smoking"],
                "no": ["non smoker", "non smokers", "nonsmoker", "nonsmokers"],
            },
        }

        matches = []

        for column in df.columns:
            for value in df[column].dropna().unique():
                actual_value = str(value).strip()
                normalized_value = self._normalize(actual_value)

                candidates = [normalized_value]

                aliases = category_aliases.get(
                    self._normalize(column), {}
                )
                candidates.extend(aliases.get(normalized_value, []))

                for candidate in candidates:
                    if not candidate:
                        continue

                    pattern = (
                        r"(?<![a-z0-9])"
                        + re.escape(candidate)
                        + r"(?![a-z0-9])"
                    )

                    if re.search(pattern, normalized_question):
                        matches.append(
                            (column, actual_value, len(candidate))
                        )

        if not matches:
            return None

        matches.sort(key=lambda item: item[2], reverse=True)

        column, value, _ = matches[0]
        return column, value

    def answer(self, question, csv_path):

        try:
            df = self._load_csv(csv_path)

            normalized_question = self._normalize(question)
            total_rows = len(df)
            total_columns = len(df.columns)

            # 1. Category counting
            category_match = self._find_category_value(question, df)

            asks_for_count = any(
                word in normalized_question.split()
                for word in [
                    "count", "number", "total", "how", "many",
                    "records", "rows", "entries", "present",
                    "available", "there",
                ]
            )

            if category_match and asks_for_count:
                column, value = category_match

                count = int(
                    df[column]
                    .astype(str)
                    .str.strip()
                    .str.casefold()
                    .eq(str(value).strip().casefold())
                    .sum()
                )

                return {
                    "success": True,
                    "answer": (
                        f"The total number of {value} records is "
                        f"{count} out of {total_rows} rows in the dataset."
                    ),
                    "operation": "category_count",
                    "column": column,
                    "category": value,
                    "result": count,
                    "total_rows": total_rows,
                    "total_columns": total_columns,
                    "dataset": Path(csv_path).name,
                    "method": f"Count rows where {column} equals {value}",
                }

            # 2. Total row count
            row_count_phrases = [
                "total rows",
                "total records",
                "total entries",
                "number of rows",
                "number of records",
                "total dataset",
                "dataset size",
            ]

            if asks_for_count and any(
                phrase in normalized_question
                for phrase in row_count_phrases
            ):
                return {
                    "success": True,
                    "answer": f"The dataset contains {total_rows} rows.",
                    "operation": "row_count",
                    "result": total_rows,
                    "total_rows": total_rows,
                    "total_columns": total_columns,
                    "dataset": Path(csv_path).name,
                    "method": "Count all rows in the CSV",
                }

            # 3. Numeric calculations
            column = self._find_column(question, df)

            if column is None:
                return {
                    "success": False,
                    "answer": "I could not identify the dataset column. Please mention a column name.",
                    "dataset": Path(csv_path).name,
                }

            numeric_values = pd.to_numeric(
                df[column],
                errors="coerce"
            ).dropna()

            if numeric_values.empty:
                return {
                    "success": False,
                    "answer": f"Column '{column}' does not contain numeric data.",
                    "dataset": Path(csv_path).name,
                }

            words = normalized_question.split()

            if "average" in words or "mean" in words:
                result = float(numeric_values.mean())
                operation = "average"
                answer = f"The average of {column} is {result:,.2f}."

            elif any(
                word in words
                for word in ["maximum", "max", "highest", "largest"]
            ):
                result = float(numeric_values.max())
                operation = "maximum"
                answer = f"The maximum value of {column} is {result:,.2f}."

            elif any(
                word in words
                for word in ["minimum", "min", "lowest", "smallest"]
            ):
                result = float(numeric_values.min())
                operation = "minimum"
                answer = f"The minimum value of {column} is {result:,.2f}."

            elif "sum" in words or "total" in words:
                result = float(numeric_values.sum())
                operation = "sum"
                answer = f"The total sum of {column} is {result:,.2f}."

            else:
                return {
                    "success": False,
                    "answer": "I could not identify the requested calculation.",
                    "column": column,
                    "dataset": Path(csv_path).name,
                }

            return {
                "success": True,
                "answer": answer,
                "operation": operation,
                "column": column,
                "result": result,
                "total_rows": total_rows,
                "total_columns": total_columns,
                "dataset": Path(csv_path).name,
                "method": f"Calculate {operation} using all non-empty numeric values in {column}",
            }

        except Exception as exc:
            return {
                "success": False,
                "answer": f"CSV analysis failed: {str(exc)}",
                "error": str(exc),
            }


structured_data_agent = StructuredDataAgent()

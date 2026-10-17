"""Parse POLA Wharfinger 'Historical Container Vessel Activity' 2024 PDF -> data/ext/pola_daily.parquet.

Independent ground truth (Port of LA, container vessels only, business days) to validate our AIS counts.
Source PDF (Cloudflare blocks scripts; download by hand into data/ext/pola/):
https://portoflosangeles.org/business/supply-chain/ships -> "CY 2024"
"""
import re
from glob import glob
import pandas as pd
import pdfplumber

ROW = re.compile(r"^(\d{1,2}/\d{1,2}/\d{4})\s+(\d+)\s+(\d+)\s+(\d+)\s+([\d.]+)\s+([\d.]+)$")


def main():
    pdf = glob("data/ext/pola/*Vessel-Activity-Summary-2024*.pdf")[0]
    rows = []
    with pdfplumber.open(pdf) as p:
        for page in p.pages:
            for line in page.extract_text().splitlines():
                m = ROW.match(line.strip())
                if m:
                    rows.append(m.groups())
    d = pd.DataFrame(rows, columns=["date", "pola_anchor", "pola_berth", "pola_departed",
                                    "pola_days_berth", "pola_days_anc_berth"])
    d["date"] = pd.to_datetime(d.date, format="%m/%d/%Y")
    d = d.astype({c: float for c in d.columns if c != "date"})
    d.to_parquet("data/ext/pola_daily.parquet", index=False)
    print(len(d), "days;", d.describe().T.round(2).to_string())


if __name__ == "__main__":
    main()

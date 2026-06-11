#!/usr/bin/env python3
"""slr_pipeline.py — pipeline da SLR (Kitchenham-light).

Uso:
  python slr_pipeline.py merge  slr/exports/*.csv -o slr/triagem.csv
  python slr_pipeline.py stats  slr/triagem.csv

Coloque em slr/exports/ os CSVs exportados das bases (Scopus, IEEE,
WoS, ACM). O merge normaliza colunas, deduplica (DOI exato, depois
título normalizado com similaridade >= 0.93) e gera a planilha de
triagem com colunas de decisão para as fases 1 e 2.
"""
import argparse
import re
import sys
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd

# Mapeamento de nomes de coluna por base -> nome canônico
COLMAP = {
    "title": ["title", "document title", "article title", "ti"],
    "authors": ["authors", "author full names", "au", "author(s)"],
    "year": ["year", "publication year", "py", "date"],
    "venue": ["source title", "publication title", "venue", "so", "journal"],
    "doi": ["doi", "di"],
    "abstract": ["abstract", "ab"],
}

SCREEN_COLS = [
    "fase1_decisao",  # I / E / DUVIDA
    "fase1_motivo",   # ex.: E1, E3, I1+I2
    "fase2_decisao",
    "fase2_motivo",
    "qualidade",      # soma Q1..Q5 (fase 2)
    "revisado_humano",  # S/N — marque S na amostra test-retest
]


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9 ]", " ", s.lower()).strip()


def canonicalize(df: pd.DataFrame, source: str) -> pd.DataFrame:
    low = {c.lower().strip(): c for c in df.columns}
    out = pd.DataFrame()
    for canon, aliases in COLMAP.items():
        col = next((low[a] for a in aliases if a in low), None)
        out[canon] = df[col] if col else ""
    out["base"] = source
    # ano como inteiro quando possível
    out["year"] = pd.to_numeric(out["year"], errors="coerce").astype("Int64")
    return out


def dedupe(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    n0 = len(df)
    # 1) DOI exato (não-vazio)
    df["_doi"] = df["doi"].map(norm)
    has_doi = df["_doi"].str.len() > 4
    df = pd.concat([
        df[has_doi].drop_duplicates("_doi"),
        df[~has_doi],
    ])
    # 2) título normalizado: exato, depois fuzzy O(n²) nos restantes
    df["_t"] = df["title"].map(norm)
    df = df.drop_duplicates("_t").reset_index(drop=True)
    keep, titles = [], []
    for i, t in enumerate(df["_t"]):
        dup = any(SequenceMatcher(None, t, u).ratio() >= 0.93 for u in titles)
        if not dup:
            keep.append(i)
            titles.append(t)
    df = df.loc[keep].drop(columns=["_doi", "_t"]).reset_index(drop=True)
    return df, n0 - len(df)


def cmd_merge(args):
    frames = []
    for p in args.inputs:
        path = Path(p)
        raw = pd.read_csv(path, dtype=str, on_bad_lines="skip",
                          encoding_errors="replace")
        frames.append(canonicalize(raw, path.stem))
        print(f"  {path.name}: {len(raw)} registros")
    df = pd.concat(frames, ignore_index=True)
    df, removed = dedupe(df)
    df.insert(0, "id", [f"P{i:04d}" for i in range(1, len(df) + 1)])
    for c in SCREEN_COLS:
        df[c] = ""
    df.to_csv(args.output, index=False)
    print(f"Total bruto: {len(df) + removed} | duplicatas removidas: "
          f"{removed} | para triagem: {len(df)} -> {args.output}")


def cmd_stats(args):
    df = pd.read_csv(args.input, dtype=str).fillna("")
    n = len(df)
    f1 = df["fase1_decisao"].str.upper().str.strip()
    f2 = df["fase2_decisao"].str.upper().str.strip()
    print(f"Identificados (pós-dedup): {n}")
    print(f"Fase 1 — Incluídos: {(f1 == 'I').sum()} | Excluídos: "
          f"{(f1 == 'E').sum()} | Dúvida: {(f1 == 'DUVIDA').sum()} | "
          f"Pendentes: {(f1 == '').sum()}")
    print(f"Fase 2 — Incluídos: {(f2 == 'I').sum()} | Excluídos: "
          f"{(f2 == 'E').sum()} | Pendentes: "
          f"{((f1 == 'I') & (f2 == '')).sum()}")
    if (f1 == "E").any():
        print("Motivos de exclusão (fase 1):")
        print(df.loc[f1 == "E", "fase1_motivo"].str.upper()
                .value_counts().to_string())
    rev = (df["revisado_humano"].str.upper() == "S").sum()
    print(f"Revisados por humano (test-retest): {rev} "
          f"({100 * rev / max(n, 1):.0f}%)")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("merge")
    m.add_argument("inputs", nargs="+")
    m.add_argument("-o", "--output", default="slr/triagem.csv")
    m.set_defaults(func=cmd_merge)
    s = sub.add_parser("stats")
    s.add_argument("input")
    s.set_defaults(func=cmd_stats)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    sys.exit(main())

"""Press release ETL: JSONL → parquet.

Reads all *.jsonl under data/congress_press/ and writes:
  parquet/press.parquet  — one row per release (member metadata + text)

Run inside the lobbypress-analysis docker image. Source = data/.
"""
from __future__ import annotations
import argparse, json, sys, os, glob
from pathlib import Path
import pyarrow as pa, pyarrow.parquet as pq
from tqdm import tqdm


def iter_releases(press_root: Path):
    files = sorted(glob.glob(str(press_root / "**/*.jsonl"), recursive=True))
    files += sorted(glob.glob(str(press_root / "*.jsonl")))
    files = sorted(set(files))
    for p in tqdm(files, desc="press files"):
        with open(p) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                m = rec.get("member") or {}
                yield {
                    "url": rec.get("url"),
                    "title": rec.get("title"),
                    "date": rec.get("date"),
                    "date_source": rec.get("date_source"),
                    "source": rec.get("source"),
                    "domain": rec.get("domain"),
                    "scraper": rec.get("scraper"),
                    "bioguide_id": m.get("bioguide_id"),
                    "member_name": m.get("name"),
                    "party": m.get("party"),
                    "state": m.get("state"),
                    "chamber": m.get("chamber"),
                    "text": rec.get("text") or "",
                    "title_lc": (rec.get("title") or "").lower(),
                    "text_lc": (rec.get("text") or "").lower(),
                    "word_count": len((rec.get("text") or "").split()),
                }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--press_root", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    rows = []
    schema = pa.schema([
        ("url", pa.string()), ("title", pa.string()), ("date", pa.string()),
        ("date_source", pa.string()), ("source", pa.string()), ("domain", pa.string()),
        ("scraper", pa.string()), ("bioguide_id", pa.string()), ("member_name", pa.string()),
        ("party", pa.string()), ("state", pa.string()), ("chamber", pa.string()),
        ("text", pa.string()), ("title_lc", pa.string()), ("text_lc", pa.string()),
        ("word_count", pa.int64()),
    ])
    writer = pq.ParquetWriter(args.out, schema, compression="zstd")
    batch = []
    BATCH = 5000
    n = 0
    for r in iter_releases(Path(args.press_root)):
        batch.append(r)
        if len(batch) >= BATCH:
            writer.write_table(pa.Table.from_pylist(batch, schema=schema))
            n += len(batch); batch = []
    if batch:
        writer.write_table(pa.Table.from_pylist(batch, schema=schema))
        n += len(batch)
    writer.close()
    print(f"wrote {n} releases -> {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Render publication-quality charts from CSV findings."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


STYLE = {
    "figure.figsize": (12, 7.5),
    "figure.dpi": 120,
    "savefig.dpi": 200,
    "axes.titlesize": 14,
    "axes.titleweight": "normal",
    "axes.titlepad": 8,
    "axes.labelsize": 12,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": False,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
}
PRIMARY = "#0d3b66"
HIGHLIGHT = "#ee964b"
NEUTRAL = "#9ca3af"


def _hash_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_commit() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return None


def _set_style():
    plt.rcParams.update(STYLE)


def _human_money(v):
    if v is None or pd.isna(v):
        return ""
    v = float(v)
    if abs(v) >= 1e9:
        return f"${v/1e9:.1f}B"
    if abs(v) >= 1e6:
        return f"${v/1e6:.1f}M"
    if abs(v) >= 1e3:
        return f"${v/1e3:.0f}K"
    return f"${v:.0f}"


def _footer(fig, source: str, df_path: str):
    txt = f"Source: {source}.\nInput: {os.path.basename(df_path)}."
    fig.text(0.01, 0.01, txt, fontsize=8, color="#555", ha="left", va="bottom")


def render_bar(df, x_col, y_col, args):
    _set_style()
    df = df.copy()
    df = df.sort_values(y_col, ascending=True)
    if args.top:
        df = df.tail(args.top)
    fig, ax = plt.subplots()
    colors = [PRIMARY] * len(df)
    if args.highlight_col and args.highlight_value:
        colors = [HIGHLIGHT if str(v) == args.highlight_value else PRIMARY for v in df[args.highlight_col]]
    ax.barh(df[x_col].astype(str), df[y_col], color=colors)
    if args.money:
        ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: _human_money(v)))
        for i, (label, val) in enumerate(zip(df[x_col].astype(str), df[y_col])):
            ax.text(val, i, "  " + _human_money(val), va="center", fontsize=9, color="#333")
    if args.subtitle:
        fig.suptitle(args.title, fontsize=16, fontweight="bold", x=0.02, ha="left", y=0.98)
        ax.set_title(args.subtitle, fontsize=11, fontstyle="italic", color="#555", loc="left", pad=10)
    else:
        ax.set_title(args.title, loc="left")
    if args.xlabel:
        ax.set_xlabel(args.xlabel)
    if args.ylabel:
        ax.set_ylabel(args.ylabel)
    plt.tight_layout(rect=[0, 0.04, 1, 0.92])
    _footer(fig, args.source, args.in_path)
    return fig


def render_line(df, x_col, y_col, args):
    _set_style()
    df = df.copy()
    if df[x_col].dtype == object:
        try:
            df[x_col] = pd.to_datetime(df[x_col])
        except Exception:
            pass
    df = df.sort_values(x_col)
    fig, ax = plt.subplots()
    if args.group_col:
        for name, grp in df.groupby(args.group_col):
            ax.plot(grp[x_col], grp[y_col], label=str(name), linewidth=2)
        ax.legend(loc="best", frameon=False)
    else:
        ax.plot(df[x_col], df[y_col], color=PRIMARY, linewidth=2.5)
    if args.subtitle:
        fig.suptitle(args.title, fontsize=16, fontweight="bold", x=0.02, ha="left", y=0.98)
        ax.set_title(args.subtitle, fontsize=11, fontstyle="italic", color="#555", loc="left", pad=10)
    else:
        ax.set_title(args.title, loc="left")
    if args.xlabel:
        ax.set_xlabel(args.xlabel)
    if args.ylabel:
        ax.set_ylabel(args.ylabel)
    if args.money:
        ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: _human_money(v)))
    ax.grid(axis="y", color="#eee", linewidth=0.8)
    plt.tight_layout(rect=[0, 0.04, 1, 0.92])
    _footer(fig, args.source, args.in_path)
    return fig


def render_scatter(df, x_col, y_col, args):
    _set_style()
    fig, ax = plt.subplots()
    ax.scatter(df[x_col], df[y_col], color=PRIMARY, alpha=0.6, s=40)
    if args.label_col:
        for _, r in df.iterrows():
            ax.annotate(str(r[args.label_col])[:30], (r[x_col], r[y_col]), fontsize=8, alpha=0.7)
    if args.subtitle:
        fig.suptitle(args.title, fontsize=16, fontweight="bold", x=0.02, ha="left", y=0.98)
        ax.set_title(args.subtitle, fontsize=11, fontstyle="italic", color="#555", loc="left", pad=10)
    else:
        ax.set_title(args.title, loc="left")
    if args.xlabel: ax.set_xlabel(args.xlabel)
    if args.ylabel: ax.set_ylabel(args.ylabel)
    ax.grid(color="#eee", linewidth=0.8)
    plt.tight_layout(rect=[0, 0.04, 1, 0.92])
    _footer(fig, args.source, args.in_path)
    return fig


def render_area_stacked(df, x_col, y_col, args):
    _set_style()
    fig, ax = plt.subplots()
    if args.group_col:
        pivot = df.pivot_table(index=x_col, columns=args.group_col, values=y_col, aggfunc="sum").fillna(0)
        ax.stackplot(pivot.index, pivot.T, labels=pivot.columns)
        ax.legend(loc="upper left", frameon=False, fontsize=9)
    else:
        ax.fill_between(df[x_col], df[y_col], color=PRIMARY, alpha=0.6)
    if args.subtitle:
        fig.suptitle(args.title, fontsize=16, fontweight="bold", x=0.02, ha="left", y=0.98)
        ax.set_title(args.subtitle, fontsize=11, fontstyle="italic", color="#555", loc="left", pad=10)
    else:
        ax.set_title(args.title, loc="left")
    if args.xlabel: ax.set_xlabel(args.xlabel)
    if args.ylabel: ax.set_ylabel(args.ylabel)
    if args.money:
        ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: _human_money(v)))
    plt.tight_layout(rect=[0, 0.04, 1, 0.92])
    _footer(fig, args.source, args.in_path)
    return fig


def render_slope(df, x_col, y_col, args):
    """Slope chart for before/after: x_col must have exactly 2 values per group."""
    _set_style()
    fig, ax = plt.subplots()
    if args.group_col:
        groups = list(df[args.group_col].unique())
        for name in groups:
            grp = df[df[args.group_col] == name].sort_values(x_col)
            if len(grp) < 2:
                continue
            ax.plot(grp[x_col], grp[y_col], "-o", linewidth=1.6, alpha=0.85)
            ax.text(grp.iloc[-1][x_col], grp.iloc[-1][y_col], "  " + str(name)[:30], fontsize=9, va="center")
    if args.subtitle:
        fig.suptitle(args.title, fontsize=16, fontweight="bold", x=0.02, ha="left", y=0.98)
        ax.set_title(args.subtitle, fontsize=11, fontstyle="italic", color="#555", loc="left", pad=10)
    else:
        ax.set_title(args.title, loc="left")
    if args.money:
        ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: _human_money(v)))
    if args.xlabel: ax.set_xlabel(args.xlabel)
    if args.ylabel: ax.set_ylabel(args.ylabel)
    plt.tight_layout(rect=[0, 0.04, 1, 0.92])
    _footer(fig, args.source, args.in_path)
    return fig


RENDERERS = {
    "bar": render_bar,
    "line": render_line,
    "scatter": render_scatter,
    "area_stacked": render_area_stacked,
    "slope": render_slope,
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", choices=list(RENDERERS), required=True)
    ap.add_argument("--in", dest="in_path", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--x", dest="x_col", required=True)
    ap.add_argument("--y", dest="y_col", required=True)
    ap.add_argument("--group-col", default=None)
    ap.add_argument("--label-col", default=None)
    ap.add_argument("--highlight-col", default=None)
    ap.add_argument("--highlight-value", default=None)
    ap.add_argument("--title", required=True)
    ap.add_argument("--subtitle", default=None)
    ap.add_argument("--xlabel", default=None)
    ap.add_argument("--ylabel", default=None)
    ap.add_argument("--source", required=True, help="Source-line text for the footer")
    ap.add_argument("--money", action="store_true", help="Format y-axis as USD")
    ap.add_argument("--top", type=int, default=None, help="Keep only top N rows by y")
    ap.add_argument("--filter", default=None, help="pandas query string")
    args = ap.parse_args()

    df = pd.read_csv(args.in_path)
    if args.filter:
        df = df.query(args.filter)
    fig = RENDERERS[args.kind](df, args.x_col, args.y_col, args)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, bbox_inches="tight")
    svg = out.with_suffix(".svg")
    fig.savefig(svg, bbox_inches="tight")
    meta = {
        "input": str(args.in_path),
        "input_sha256": _hash_file(args.in_path),
        "kind": args.kind,
        "x_col": args.x_col,
        "y_col": args.y_col,
        "filter": args.filter,
        "top": args.top,
        "title": args.title,
        "subtitle": args.subtitle,
        "source_line": args.source,
        "git_commit": _git_commit(),
        "rows_rendered": int(len(df) if not args.top else min(args.top, len(df))),
    }
    out.with_suffix(".meta.json").write_text(json.dumps(meta, indent=2))
    print(f"Wrote {out} and {svg}")


if __name__ == "__main__":
    main()

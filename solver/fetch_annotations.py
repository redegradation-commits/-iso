"""Fetch MaleCNS annotations for the nodes in the challenge adjacency graph."""
import csv
import gzip
import os
import urllib.request

import pandas as pd

BASE = "https://storage.googleapis.com/flyem-male-cns/v1.0/connectome-data/flat-connectome/"
ANN = "body-annotations-male-cns-v1.0-minconf-0.5.feather"
NT = "body-neurotransmitters-male-cns-v1.0.feather"


def download(name):
    path = os.path.join("/tmp", name)
    if not os.path.exists(path):
        print("downloading", BASE + name, flush=True)
        urllib.request.urlretrieve(BASE + name, path)
    print(name, os.path.getsize(path), flush=True)
    return path


def main():
    os.makedirs("raw", exist_ok=True)
    nodes = set()
    with gzip.open("raw/adjacency.csv.gz", "rt") as f:
        next(f)
        for line in f:
            a, b = line.strip().split(",")
            nodes.add(int(a))
            nodes.add(int(b))
    print("graph nodes", len(nodes), min(nodes), max(nodes), flush=True)

    ann = pd.read_feather(download(ANN))
    print("annotation columns", list(ann.columns), flush=True)
    print("annotation rows", len(ann), flush=True)
    ann_sub = ann[ann["bodyId"].isin(nodes)].copy()
    print("matched annotation rows", len(ann_sub), "of", len(nodes), flush=True)
    ann_sub.to_csv("raw/annotations_subset.csv", index=False)

    nt = pd.read_feather(download(NT))
    print("nt columns", list(nt.columns), flush=True)
    body_col = "body" if "body" in nt.columns else "bodyId"
    nt_sub = nt[nt[body_col].isin(nodes)].copy()
    print("matched nt rows", len(nt_sub), flush=True)
    nt_sub.to_csv("raw/nt_subset.csv", index=False)


if __name__ == "__main__":
    main()

"""Fetch synaptic weights for the subgraph induced by the task's node set.

The handout adjacency only has topology.  The public MaleCNS connectome release
has the actual synapse counts per body_pre -> body_post pair.  We keep only rows
whose endpoints are both present in the handout graph, aggregate them, and write
small CSV files that can be committed (the full feather is ~500 MB).
"""
import gzip
import io
import os
import urllib.request

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.feather as feather

BUCKET = "https://storage.googleapis.com/flyem-male-cns/v1.0/connectome-data/flat-connectome"
FEATHER = "connectome-weights-male-cns-v1.0-minconf-0.5-significant-only.feather"
URL = f"{BUCKET}/{FEATHER}"

os.makedirs("raw", exist_ok=True)

# Node set from the handout adjacency.
nodes = set()
with gzip.open("raw/adjacency.csv.gz", "rt") as f:
    next(f)
    for line in f:
        a, b = line.rstrip("\n").split(",")
        nodes.add(int(a))
        nodes.add(int(b))
print("nodes", len(nodes), flush=True)
node_list = pa.array(sorted(nodes), type=pa.int64())

print("downloading", URL, flush=True)
with urllib.request.urlopen(URL, timeout=600) as r:
    data = r.read()
print("downloaded", len(data), flush=True)
open("/tmp/weights.feather", "wb").write(data)

table = feather.read_table("/tmp/weights.feather")
print("schema:", table.schema, flush=True)
print("rows:", table.num_rows, flush=True)
with open("raw/weights_schema.txt", "w") as f:
    f.write(f"file={FEATHER}\nrows={table.num_rows}\n{table.schema}\n")

cols = set(table.column_names)
# Be tolerant about exact column spelling.
def pick(*names):
    for n in names:
        if n in cols:
            return n
    raise SystemExit(f"missing any of {names}; columns={sorted(cols)}")

pre = pick("body_pre", "pre", "bodyPre")
post = pick("body_post", "post", "bodyPost")
weight = pick("weight", "synapses", "count")

# Filter to the induced subgraph.
mask = pc.and_(pc.is_in(table[pre], value_set=node_list),
               pc.is_in(table[post], value_set=node_list))
sub = table.filter(mask)
print("induced rows", sub.num_rows, flush=True)

sub = sub.select([pre, post, weight])
with open("raw/weights_subset.csv.gz", "wb") as f:
    sub.to_pandas().to_csv(f, index=False, compression="gzip")

# Aggregate duplicate directed pairs.
df = sub.to_pandas()
agg = (df.groupby([pre, post], as_index=False)[weight]
         .agg(weight_sum="sum", n_rows="size"))
agg.to_csv("raw/weights_pair.csv.gz", index=False, compression="gzip")
print("aggregated pairs", len(agg), flush=True)
print(agg.head(), flush=True)

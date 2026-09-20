import os, json, time, sys

reporoot = r'C:\Users\Administrator\Documents\Default Project\discovery-evidence-fabric'
os.chdir(reporoot)
sys.path.insert(0, reporoot)

from discovery_fabric.retrieval_fabric import pipeline as fabric_pipeline
from tests.test_r512_retrieve_fanout import PROBLEM

def run_mode(mode):
    for k in list(os.environ.keys()):
        if k.startswith('ENGINE_'):
            del os.environ[k]
    os.environ['ENGINE_RETRIEVE_FANOUT'] = mode
    t0 = time.time()
    items, report = fabric_pipeline.retrieve_fabric(PROBLEM, enable_reciprocal=False, enable_unpaywall=False)
    wall = time.time() - t0
    a = report['retrieval_attribution']
    return items, wall, a

# Run serial and parallel back-to-back
items_s, wall_s, a_s = run_mode('serial')
items_p, wall_p, a_p = run_mode('parallel')

print(f'SERIAL  wall={wall_s:.2f}s n_items={len(items_s)} records={a_s["records_returned"]} admitted={a_s["records_admitted"]}')
print(f'PARALLEL wall={wall_p:.2f}s n_items={len(items_p)} records={a_p["records_returned"]} admitted={a_p["records_admitted"]}')

# Compare evidence content deeply
def canonicalize(items):
    # Extract comparable identity from each item
    out = []
    for it in items:
        if isinstance(it, dict):
            # collect key fields
            out.append({k: it.get(k) for k in ('source', 'source_id', 'uri', 'url', 'title', 'doi', 'patent_id', 'identifier') if k in it})
        else:
            out.append(str(it))
    return out

c_s = canonicalize(items_s)
c_p = canonicalize(items_p)
print('\nSERIAL item keys sample:', json.dumps(c_s[:3], default=str)[:500])
print('PARALLEL item keys sample:', json.dumps(c_p[:3], default=str)[:500])

# Compare by identity set
set_s = {json.dumps(x, sort_keys=True, default=str) for x in c_s}
set_p = {json.dumps(x, sort_keys=True, default=str) for x in c_p}
print(f'\nunique serial: {len(set_s)}, unique parallel: {len(set_p)}')
print(f'identical sets: {set_s == set_p}')
print(f'serial-only: {len(set_s - set_p)}, parallel-only: {len(set_p - set_s)}')
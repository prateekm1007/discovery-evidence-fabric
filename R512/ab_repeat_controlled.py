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
    return {
        'mode': a['mode'],
        'wall_s': wall,
        'records_returned': a['records_returned'],
        'records_admitted': a['records_admitted'],
        'max_workers_effective': a['max_workers_effective'],
        'peak_concurrency': a['peak_concurrency_observed'],
        'worker_queue_wait_s': a['worker_queue_wait_s'],
        'canonical_merges': a['canonical_merges'],
        'enrichment_s': a['enrichment_s'],
        'n_jobs': a['n_jobs'],
        'n_items': len(items),
    }

REPS = 3
print('REPS:', REPS)
serial_results = []
parallel_results = []
for i in range(REPS):
    s = run_mode('serial')
    p = run_mode('parallel')
    serial_results.append(s)
    parallel_results.append(p)
    print(f'\n=== REP {i+1} ===')
    print(f'SERIAL  wall={s["wall_s"]:.2f}s ret={s["records_returned"]} adm={s["records_admitted"]} workers={s["max_workers_effective"]} peak={s["peak_concurrency"]} queue_wait={s["worker_queue_wait_s"]:.3f}s merges={s["canonical_merges"]} enrich={json.dumps(s["enrichment_s"])} jobs={s["n_jobs"]} items={s["n_items"]}')
    print(f'PARALLEL wall={p["wall_s"]:.2f}s ret={p["records_returned"]} adm={p["records_admitted"]} workers={p["max_workers_effective"]} peak={p["peak_concurrency"]} queue_wait={p["worker_queue_wait_s"]:.3f}s merges={p["canonical_merges"]} enrich={json.dumps(p["enrichment_s"])} jobs={p["n_jobs"]} items={p["n_items"]}')

# Aggregate
import statistics
s_walls = [r['wall_s'] for r in serial_results]
p_walls = [r['wall_s'] for r in parallel_results]
print('\n=== AGGREGATE ===')
print(f'SERIAL  mean={statistics.mean(s_walls):.2f}s min={min(s_walls):.2f} max={max(s_walls):.2f} stdev={statistics.stdev(s_walls):.2f}')
print(f'PARALLEL mean={statistics.mean(p_walls):.2f}s min={min(p_walls):.2f} max={max(p_walls):.2f} stdev={statistics.stdev(p_walls):.2f}')
deltas = [(p - s) for s, p in zip(s_walls, p_walls)]
pcts = [d / s * 100 for s, d in zip(s_walls, deltas)]
print(f'DELTAS  mean={statistics.mean(deltas):+.2f}s ({statistics.mean(pcts):+.1f}%)')
print(f'PCTS    {[f"{x:+.1f}%" for x in pcts]}')
print(f'serial faster in {sum(1 for d in deltas if d > 0)}/{REPS} reps')
# B1 Observation-Persistence Playbook (R510) — encode one working option before any resubmit

Status: sandbox kills detached processes (established R437; re-observed R510-C1 on
Windows). A held-open 48h daemon is therefore not a persistence strategy. The encoded
option is (i) desktop-scheduler single-tick polling (preferred). Option (ii) held-open
session and option (iii) terminal-only harvest are documented fallbacks, weakest last.

## Option (i) — scheduler single-tick (PREFERRED, implemented this round)

Instrument: `scripts/r510_observe_tick.py` — stateless wrapper around
`scripts/r509_battery_watchdog.py --live --once`. Each tick appends one JSONL row to
`R510/WATCHDOG_TICK_LOG.jsonl`; watchdog alerts append to
`R510/WATCHDOG_TICK_ALERTS.jsonl`. Observer-side only: read-only Space GETs plus a
durable-branch fetch. Never touches workers, never resubmits, never writes secrets
(BS-021). A tick failure records `OBSERVATION_GAP` about the watcher — never evidence
about the watched runs (Art. LXXIV/XXV).

Windows lesson encoded (measured R510-C1): the watchdog shells out to plain `git`,
absent from PATH on stock Windows (`WinError 2` -> fail-closed gap). The tick script
prepends standard install locations when `git` is unresolvable. Private-remote fetch
needs the operator's PAT in the scheduler environment (the LXXIII vault pattern);
without it the tick records a fetch gap, still fail-closed.

Scheduler wiring (operator machine):

```text
Windows Task Scheduler, every 5 min, action:
  python <repo>\scripts\r510_observe_tick.py
cron equivalent:
  */5 * * * * /usr/bin/python3 /path/to/repo/scripts/r510_observe_tick.py
```

Acceptance evidence: `R510/REPLAY_R510_DRYRUN.json` — replay of the R508 death
signature window re-derived in-tree: 25 polls, `DURABLE_TIP_STALE` 00:50Z, then
`HEARTLESS_WORKERS` 00:55Z, then `STALLED_OVER_2X_P90` 01:40Z — alert kinds,
order, and timestamps byte-identical to `R509/REPLAY_R509_SIGNATURE.json`.

## Option (ii) — held-open session (fallback)

Keep one foreground shell on the operator machine running the watchdog `--live`
loop for the run window. Valid only while the shell stays open; a closed laptop
lid ends it. Same alert log paths. Use only if the scheduler cannot be installed.

## Option (iii) — terminal-only harvest (weakest, fallback of last resort)

If no observation survives (no scheduler, no open session), harvest runs on durable
terminals only, typed per LXXIV mid-flight rule. This is the weakest option because
the R508 lesson is that terminals can exist ephemerally while the durable branch
stays silent — terminal-only harvest would have typed a live campaign as lost. Never
preferred; recorded here so the weakness is explicit, not discovered mid-campaign.

## Stop conditions

Ticks continue until harvest completes. Any tick row with `OBSERVATION_GAP` is a
watcher defect to fix (PATH, network, credential), never a campaign verdict.

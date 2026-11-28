# Article LXXXVII — The Secrets Vault (Single Store + Lookup-First)

**Ratified:** 2026-11-14 (Round R11)
**Amends:** Constitution v2.11.0 -> v2.12.0
**Full text:** `R11/constitution/ARTICLE_LXXXVII_THE_SECRETS_VAULT.md`
**Sponsor:** Operator directive, 2026-11-14 ("put all secrets like PAT
and tokens for AI models and other important secrets in your vault,
and add that all secrets are saved in vault in your constitution,
which you will look up whenever you need keys, pat, etc" — delivered
with a rotated GitHub PAT).

### The rule

1. **ONE store.** Every secret the machine holds — GitHub PATs, AI
   provider keys, deployment tokens, anything the operator hands over
   — lives in THE VAULT: the gitignored credential file `.env.keys`
   at the repo root (KEY=VALUE lines, '#' comments). `SECRETS_VAULT`
   may point the loaders at an alternative store; absent that
   override, `.env.keys` is the vault of record for this sandbox.
2. **Lookup-first.** Whenever the machine needs a key, a PAT, or any
   credential, it LOOKS IT UP IN THE VAULT FIRST — via the loaders
   (`r7_queue_runner._load_key_vault`,
   `discovery_fabric.engine.adapters.load_credentials`; lookup order:
   process env wins > explicit path > `.env.keys` >
   `$SECRETS_VAULT`) — and only asks the operator when the name is
   absent from every vault location. Asking for a credential the
   vault already holds is a defect (this closes the 2026-09-16
   loop with Art. LXXIII: the operator should have to hand a secret
   over ONCE).
3. **Arrival custody.** A secret arriving from the operator (chat,
   ticket, file) goes into the vault FIRST, before any use. Using a
   secret without custody is a violation even when the use succeeds.
4. **Never tracked, never logged, never echoed.** Secrets appear in
   exactly one untracked file. They never enter a tracked file, a
   commit, a log line, or a command output; verification is by NAME
   + SHA-256 fingerprint only (Art. LXXVI discipline). A secret
   found in a tracked file is an incident to fix immediately
   (history: the PAT + provider keys leaked into tracked files once —
   the secret-scan step exists because of that).
5. **Rotation.** The operator owns rotation (Art. LXXVI); when a
   rotated value arrives, the vault entry is REPLACED in place and
   every stored copy of the old value outside the vault (remote URLs,
   config caches) is updated or removed in the same session — a
   stale credential outside the vault is a latent failure, not a
   backup.

### Serves

Art. LXXIII (lookup before asking), Art. LXXVI (custody, names +
fingerprints), Art. X (transport plumbing only), Art. XXXI (every
correction creates a memory artifact), Art. LXXXV (push for
auditability — the vault itself stays untracked; the AMENDMENT
 RECORD travels).

### Amendment record

See `R11/constitution/AMENDMENT_RECORD_LXXXVII.json`.

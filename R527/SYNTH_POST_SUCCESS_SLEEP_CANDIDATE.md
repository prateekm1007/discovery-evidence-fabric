# R527 Q2 — smallest behavior-neutral attribution/gate addition to
# represent SYNTHESIZE_POST_SUCCESS_SLEEP as a measured, typed
# candidate class. This file is governance-only: it names the
# candidate + states the counterfactual; it does NOT alter engine
# behavior. The engine change (removing the fixed 0.5 s post-success
# sleep in a2/synthesize.llm_chat) is the after-arm intervention,
# applied only after the nine-criterion gate is satisfied.
#
# Candidate: SYNTHESIZE_POST_SUCCESS_SLEEP
#   source: discovery_fabric/a2/synthesize.py llm_chat()
#   measured: G_synthesize_decomposition aggregate post_success_sleep_s
#     (baseline ~0.5 s mean on all SYNTHESIZE-executed rows)
#   causal attribution: the fixed time.sleep(0.5) after a successful
#     reg.generate() return — a single typed code line, not a
#     generate() routing subphase (that is class A) nor a post-rank
#     subphase (class B) nor a retrieval source (class D).
#   counterfactual (Z): remove the fixed 0.5 s post-success sleep.
#     Bounded, non-prohibited: it does not touch prompt, model,
#     provider order, provider retirement, token budget, max_retries,
#     admission logic, routing semantics, retrieval, mechanism-space
#     logic, evidence gates, parsing, candidate assembly, or funnel
#     logic. The rotation backoff sleeps (0/8/20 s, failure-class
#     response) are a separate mechanism and are NOT touched.
#   claimed wall decrease: ~0.5 s per successful SYNTHESIZE call
#     (10/10 in the R526 S5 fresh battery).

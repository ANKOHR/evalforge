# Evaluation methodology

## Dataset design

The flagship RAG fixture contains 120 labelled cases: 72 train, 24 dev and 24 held out. It includes supported answers, absent evidence, distractor passages, conflicting sources and paraphrased questions. Each case records expected facts, citations, refusal state, difficulty, tags and failure category.

The agent fixture contains 50 tool-policy cases. Each case specifies the expected tool sequence and arguments, with high-value cases routed to a review decision rather than an unauthorized action.

## Graders

Deterministic graders run before any optional judge: facts and citations are compared to labelled evidence, structured fields are checked against declared types, numeric values use explicit tolerance, and tool calls are compared by name and arguments. A candidate cannot pass because it sounds plausible.

## Metrics

RAG reports answer fact correctness, citation presence/correctness, retrieval recall@3, MRR, refusal correctness, unsupported-claim rate, latency mean/p95 and estimated cost/query. Agent reports task completion, tool sequence accuracy, argument correctness and policy-oriented failures.

Every report includes per-case grader results and grouped labels so a single aggregate cannot hide why a candidate failed.

## Release decision

`compare` evaluates baseline versus candidate against gates. In the public fixture, candidate v2 improves facts from 91.67% to 100% and p95 latency, but citation correctness falls from 95.83% to 87.50% and unsupported claims rise to 4.17%. The correct result is `BLOCK_RELEASE`.

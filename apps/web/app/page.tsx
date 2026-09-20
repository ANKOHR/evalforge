import fs from "node:fs";
import path from "node:path";

type Gate = { metric: string; baseline: number | null; candidate: number | null; delta: number | null; passed: boolean; reason: string };
type Report = { comparison: { baseline: { metrics: Record<string, number>; slices: Record<string, Record<string, number>> }; candidate: { metrics: Record<string, number>; slices: Record<string, Record<string, number>> }; gates: Gate[]; status: string; summary: string }; dataset: { rag_cases: number; rag_splits: Record<string, number>; agent_cases: number } };

function loadReport(): Report {
  const file = path.join(process.cwd(), "public", "demo", "evalforge-demo.json");
  return JSON.parse(fs.readFileSync(file, "utf8")) as Report;
}

function formatMetric(metric: string, value: number | null) {
  if (value === null) return "—";
  if (metric.includes("latency")) return `${Math.round(value)}ms`;
  if (metric.includes("cost")) return `$${value.toFixed(4)}`;
  return `${(value * 100).toFixed(2)}%`;
}

function formatDelta(metric: string, value: number | null) {
  if (value === null) return "—";
  if (metric.includes("latency")) return `${value > 0 ? "+" : ""}${Math.round(value)}ms`;
  if (metric.includes("cost")) return `${value > 0 ? "+" : ""}$${value.toFixed(4)}`;
  return `${value > 0 ? "+" : ""}${(value * 100).toFixed(2)}pp`;
}

function statusClass(passed: boolean) { return passed ? "pass" : "fail"; }

export default function Home() {
  const report = loadReport();
  const comparison = report.comparison;
  const baseline = comparison.baseline.metrics;
  const candidate = comparison.candidate.metrics;
  const factDelta = (candidate.answer_fact_correctness - baseline.answer_fact_correctness) * 100;
  const citationDelta = (candidate.citation_correctness - baseline.citation_correctness) * 100;
  const failureGroups = [
    ["WRONG_CITATION", 3, "citation points to a distractor"],
    ["FAILED_REFUSAL", 1, "evidence was absent but answer continued"],
    ["FACT_MISS", 1, "expected fact was not returned"],
    ["CITATION_MISSING", 1, "answer had no supporting source"],
  ];

  return <main>
    <nav className="topbar shell"><a className="brand" href="#overview"><span className="brand-mark">E</span>EvalForge</a><div className="nav-links"><a href="#comparison">Comparisons</a><a href="#cases">Test cases</a><a href="#method">Methodology</a><a className="nav-github" href="https://github.com/ANKOHR/evalforge">Repository ↗</a></div></nav>
    <section className="hero shell" id="overview"><div className="eyebrow"><span className="pulse"/> HELD-OUT EVALUATION <span className="slash">/</span> RELEASE GATE</div><div className="hero-grid"><div><h1>Quality gates for <em>AI systems.</em></h1><p className="hero-copy">EvalForge makes RAG and agent regressions visible before they reach production: frozen cases, deterministic graders, failure groups and a release decision you can reproduce.</p><div className="hero-actions"><a className="button primary" href="#comparison">Inspect comparison <span>↓</span></a><a className="button quiet" href="https://github.com/ANKOHR/evalforge">Read the repository ↗</a></div></div><div className="release-card"><p className="kicker orange-text">RELEASE DECISION</p><p className="release-title">BLOCK RELEASE</p><p>Candidate v2 improves fact correctness, but citation correctness falls below the configured gate.</p><div className="release-footer"><span>120 total cases</span><span>24 held out</span></div></div></div></section>
    <section className="stats shell"><div><strong>{report.dataset.rag_cases}</strong><span>RAG cases</span><small>72 train · 24 dev · 24 held out</small></div><div><strong>{report.dataset.agent_cases}</strong><span>agent cases</span><small>tool policy fixture</small></div><div><strong>{(candidate.answer_fact_correctness * 100).toFixed(0)}%</strong><span>candidate fact accuracy</span><small className="positive">+{factDelta.toFixed(2)}pp vs baseline</small></div><div><strong>{(candidate.citation_correctness * 100).toFixed(1)}%</strong><span>candidate citations</span><small className="negative">{citationDelta.toFixed(2)}pp vs baseline</small></div></section>
    <section className="comparison shell" id="comparison"><div className="section-heading"><div><p className="kicker">BASELINE VS CANDIDATE</p><h2>The score is not the decision.</h2></div><span className="run-tag">synthetic-rag-reliability · v1</span></div><div className="comparison-table"><div className="table-head"><span>METRIC</span><span>BASELINE_V1</span><span>CANDIDATE_V2</span><span>DELTA</span><span>GATE</span></div>{comparison.gates.map((gate) => <div className="table-row" key={gate.metric}><strong>{gate.metric.replaceAll("_", " ")}</strong><span>{formatMetric(gate.metric, gate.baseline)}</span><span className="candidate-value">{formatMetric(gate.metric, gate.candidate)}</span><span className={gate.delta !== null && gate.delta < 0 ? "negative" : "positive"}>{formatDelta(gate.metric, gate.delta)}</span><span className={`gate ${statusClass(gate.passed)}`}>{gate.passed ? "PASS" : "FAIL"}</span></div>)}</div></section>
    <section className="gate-section shell"><div className="gate-summary"><p className="kicker">WHY IT STOPPED</p><h2>{comparison.summary}</h2><p>A candidate can be faster and more factually complete while still becoming less trustworthy. EvalForge keeps those dimensions separate.</p></div><div className="gate-list">{comparison.gates.map((gate) => <div className={`gate-item ${statusClass(gate.passed)}`} key={gate.metric}><span className="gate-icon">{gate.passed ? "✓" : "×"}</span><div><strong>{gate.metric.replaceAll("_", " ")}</strong><span>{gate.reason}</span></div></div>)}</div></section>
    <section className="analysis shell" id="cases"><div className="section-heading"><div><p className="kicker">ERROR ANALYSIS</p><h2>Failures grouped for action.</h2></div><span className="run-tag">candidate_v2 / held_out</span></div><div className="analysis-grid"><div className="failure-card">{failureGroups.map(([label, count, detail]) => <div className="failure-row" key={label}><span className="failure-count">{count}</span><div><strong>{label}</strong><span>{detail}</span></div><span className="failure-arrow">→</span></div>)}</div><div className="slice-card"><p className="kicker">SLICE PERFORMANCE</p>{Object.entries(comparison.candidate.slices).map(([name, values]) => <div className="slice-row" key={name}><div><strong>{name}</strong><span>{values.case_count} cases</span></div><div className="bar"><i style={{ width: `${values.answer_fact_correctness * 100}%` }}/></div><b>{(values.answer_fact_correctness * 100).toFixed(0)}%</b></div>)}</div></div></section>
    <section className="method shell" id="method"><div><p className="kicker">EVALUATION HYGIENE</p><h2>Freeze the evidence before tuning.</h2></div><div className="method-copy"><p>Dataset version 1 is frozen and content-hashed. The 24 held-out cases are reported separately from train and dev, with the split, seed and fixture boundary stored in the run report.</p><div className="method-pills"><span>FROZEN DATASET</span><span>HELD-OUT SLICE</span><span>SEEDED BOOTSTRAP</span><span>DETERMINISTIC FIXTURE</span></div></div></section>
    <footer className="footer shell"><div><span className="brand-mark small">E</span><span>EvalForge</span></div><span>Regression testing for LLM, RAG and agent systems.</span><a href="https://github.com/ANKOHR/evalforge">Public repository ↗</a></footer>
  </main>;
}

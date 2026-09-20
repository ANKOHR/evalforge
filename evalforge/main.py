from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .db import create_tables

REPORT_PATH = Path(os.getenv("EVALFORGE_REPORT_PATH", "reports/evalforge-demo.json"))


@asynccontextmanager
async def lifespan(_app: FastAPI):
    create_tables()
    yield


app = FastAPI(
    title="EvalForge API",
    version="0.1.0",
    description="Regression testing for LLM, RAG and agent systems.",
    lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/health")
def health():
    return {"status": "ok", "service": "evalforge-api", "storage": "sqlalchemy"}


def _reports() -> dict:
    if not REPORT_PATH.exists():
        raise HTTPException(404, "demo report not generated; run evalforge benchmark first")
    return json.loads(REPORT_PATH.read_text(encoding="utf-8"))


@app.get("/api/demo/summary")
def demo_summary():
    reports = _reports()
    comparison = reports["comparison"]
    return {
        "dataset": reports["dataset"],
        "status": comparison["status"],
        "summary": comparison["summary"],
        "gates": comparison["gates"],
        "baseline": comparison["baseline"]["metrics"],
        "candidate": comparison["candidate"]["metrics"],
    }


@app.get("/api/demo/comparison")
def demo_comparison():
    return _reports()["comparison"]


@app.get("/api/demo/run/{candidate}")
def demo_run(candidate: str):
    reports = _reports()
    if candidate not in reports:
        raise HTTPException(404, "candidate not found")
    return reports[candidate]

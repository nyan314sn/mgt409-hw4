"""Agent run log: which tools each chat used, tokens, time, and estimated cost.

One agent_runs row per agent run (kind "chat" for a shopper's message, "summary" when old
chat is condensed). Message text is NOT stored here (it's already in chat_messages); tool
arguments are kept short. Each run is also written to the server log as one line, and
its agent-loop steps (tool calls, results, stop reason) to output/audit_trail.json (audit.py).
"""
import json
import logging
import sqlite3
import time
import uuid
from dataclasses import dataclass, field

from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.messages import ModelResponse, ToolCallPart, ToolReturnPart

import audit

from settings import MODEL_INPUT_PRICE_PER_MTOK, MODEL_OUTPUT_PRICE_PER_MTOK

log = logging.getLogger("campus_customs.agent")
if not log.handlers:  # uvicorn doesn't configure app loggers; make these lines visible
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("AGENT:    %(message)s"))
    log.addHandler(handler)
    log.setLevel(logging.INFO)
    log.propagate = False


@dataclass
class RunStats:
    kind: str
    model: str
    started: float = field(default_factory=time.perf_counter)
    status: str = "ok"
    error: str | None = None
    duration_ms: int = 0
    requests: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    tool_calls: list[dict] = field(default_factory=list)
    showcase_count: int = 0
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    steps: list[dict] = field(default_factory=list)   # agent-loop events for the audit trail

    @property
    def cost_usd(self) -> float:
        return round(self.input_tokens / 1e6 * MODEL_INPUT_PRICE_PER_MTOK
                     + self.output_tokens / 1e6 * MODEL_OUTPUT_PRICE_PER_MTOK, 6)

    def finish(self, result=None, tool_names: set[str] | None = None, error: Exception | None = None) -> "RunStats":
        self.duration_ms = int((time.perf_counter() - self.started) * 1000)
        if result is not None:
            usage = result.usage
            self.requests, self.input_tokens, self.output_tokens = usage.requests, usage.input_tokens, usage.output_tokens
            self._collect_steps(result, tool_names)
        if error is not None:
            self.status, self.error = "error", type(error).__name__
            stop = "request_limit" if isinstance(error, UsageLimitExceeded) else f"error: {type(error).__name__}"
            self.steps.append({"time": audit.now(), "step": len(self.steps) + 1, "event": "error",
                               "tool": None, "args": None, "result": None, "stop_reason": stop})
        return self

    def _collect_steps(self, result, tool_names: set[str] | None) -> None:
        """Walk the run's messages: one audit event per tool call (with its result), then
        one "final" event with the stop reason."""
        by_call_id: dict[str, dict] = {}
        step, last_response = 0, None
        for message in result.new_messages():
            if isinstance(message, ModelResponse):
                step += 1
                last_response = message
            for part in message.parts:
                if isinstance(part, ToolCallPart) and (tool_names is None or part.tool_name in tool_names):
                    args = part.args if isinstance(part.args, (dict, str)) else str(part.args)
                    text = json.dumps(args) if isinstance(args, dict) else args
                    self.tool_calls.append({"tool": part.tool_name, "args": text[:200]})
                    event = {"time": audit.now(), "step": step, "event": "tool_call", "tool": part.tool_name,
                             "args": audit.short(args), "result": None, "stop_reason": None}
                    by_call_id[part.tool_call_id] = event
                    self.steps.append(event)
                elif isinstance(part, ToolReturnPart) and part.tool_call_id in by_call_id:
                    event = by_call_id[part.tool_call_id]
                    if part.timestamp:
                        event["time"] = part.timestamp.isoformat(timespec="seconds")
                    # Never copy account details (email) into the audit file.
                    event["result"] = ("customer profile (redacted)" if part.tool_name == "get_customer_profile"
                                       else audit.short_result(part.content))
        output = result.output
        reply = getattr(output, "message", output)
        finish = getattr(last_response, "finish_reason", None)
        self.steps.append({
            "time": audit.now(), "step": step, "event": "final", "tool": "final_result",
            "args": audit.short({"product_ids": getattr(output, "product_ids", []),
                                 "showcase_title": getattr(output, "showcase_title", None)})
            if hasattr(output, "product_ids") else None,
            "result": audit.short(reply, 160),
            "stop_reason": f"final_answer ({finish})" if finish else "final_answer",
            "requests": self.requests, "tokens": [self.input_tokens, self.output_tokens], "cost_usd": self.cost_usd,
        })


def record_run(con: sqlite3.Connection, stats: RunStats, user_id: int | None, ip: str | None) -> None:
    con.execute(
        """INSERT INTO agent_runs (kind, user_id, client_ip, model, status, error, duration_ms, requests,
               input_tokens, output_tokens, cost_usd, tool_calls_json, showcase_count)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (stats.kind, user_id, ip, stats.model, stats.status, stats.error, stats.duration_ms, stats.requests,
         stats.input_tokens, stats.output_tokens, stats.cost_usd, json.dumps(stats.tool_calls), stats.showcase_count),
    )
    who = f"user:{user_id}" if user_id else "guest"
    audit.append([{"time": step["time"], "run_id": stats.run_id, "kind": stats.kind, "user": who,
                   "model": stats.model, **step} for step in stats.steps])
    tools = ", ".join(t["tool"] for t in stats.tool_calls) or "-"
    log.info("%s %s user=%s ip=%s %dms requests=%d tokens=%d/%d cost=$%.4f tools=[%s]%s",
             stats.kind, stats.status, user_id or "guest", ip, stats.duration_ms, stats.requests,
             stats.input_tokens, stats.output_tokens, stats.cost_usd, tools,
             f" error={stats.error}" if stats.error else "")


def chats_last_24h(con: sqlite3.Connection, user_id: int) -> int:
    return con.execute(
        "SELECT COUNT(*) FROM agent_runs WHERE kind = 'chat' AND user_id = ? AND created_at > datetime('now', '-1 day')",
        (user_id,),
    ).fetchone()[0]


def usage_report(con: sqlite3.Connection, days: int) -> dict:
    """Numbers for the admin usage page."""
    since = f"-{days} days"
    totals = con.execute(
        """SELECT COUNT(*) AS runs, COALESCE(SUM(status = 'error'), 0) AS errors,
                  COALESCE(SUM(input_tokens), 0) AS input_tokens, COALESCE(SUM(output_tokens), 0) AS output_tokens,
                  COALESCE(SUM(cost_usd), 0) AS cost_usd, COALESCE(AVG(duration_ms), 0) AS avg_ms,
                  COUNT(DISTINCT user_id) AS shoppers
           FROM agent_runs WHERE created_at > datetime('now', ?)""", (since,)).fetchone()
    by_day = con.execute(
        """SELECT date(created_at) AS day, COUNT(*) AS runs, COALESCE(SUM(cost_usd), 0) AS cost_usd,
                  COALESCE(SUM(input_tokens + output_tokens), 0) AS tokens
           FROM agent_runs WHERE created_at > datetime('now', ?) GROUP BY day ORDER BY day""", (since,)).fetchall()
    tool_counts: dict[str, int] = {}
    recent = []
    for r in con.execute(
        """SELECT a.*, u.email FROM agent_runs a LEFT JOIN users u ON u.id = a.user_id
           WHERE a.created_at > datetime('now', ?) ORDER BY a.id DESC""", (since,)):
        calls = json.loads(r["tool_calls_json"] or "[]")
        for c in calls:
            tool_counts[c["tool"]] = tool_counts.get(c["tool"], 0) + 1
        if len(recent) < 50:
            recent.append({
                "id": r["id"], "createdAt": r["created_at"], "kind": r["kind"], "who": r["email"] or "guest",
                "status": r["status"], "error": r["error"], "durationMs": r["duration_ms"], "requests": r["requests"],
                "inputTokens": r["input_tokens"], "outputTokens": r["output_tokens"], "costUsd": r["cost_usd"],
                "toolCalls": calls, "showcaseCount": r["showcase_count"],
            })
    return {
        "days": days,
        "prices": {"inputPerMTok": MODEL_INPUT_PRICE_PER_MTOK, "outputPerMTok": MODEL_OUTPUT_PRICE_PER_MTOK},
        "totals": {"runs": totals["runs"], "errors": totals["errors"], "inputTokens": totals["input_tokens"],
                   "outputTokens": totals["output_tokens"], "costUsd": round(totals["cost_usd"], 4),
                   "avgMs": int(totals["avg_ms"]), "shoppers": totals["shoppers"]},
        "byDay": [{"day": r["day"], "runs": r["runs"], "costUsd": round(r["cost_usd"], 4), "tokens": r["tokens"]} for r in by_day],
        "tools": sorted(({"tool": t, "calls": n} for t, n in tool_counts.items()), key=lambda x: -x["calls"]),
        "recent": recent,
    }

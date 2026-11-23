"""Thin wrapper around the Anthropic SDK: forced tool call -> validated pydantic object, plus a usage meter."""
import threading, time
from . import config
from .util import append_jsonl, today

_client = None
def client():
    global _client
    if _client is None:
        from anthropic import Anthropic
        _client = Anthropic(max_retries=5)   # the SDK retries 429/5xx with exponential backoff
    return _client

class Meter:
    """Records model, prompt version, date, tokens and seconds for one step into data/runs.jsonl."""
    def __init__(self, step, stage, model):
        self.step, self.stage, self.model = step, stage, model
        self.inp = self.out = self.calls = 0; self.lock = threading.Lock()
    def add(self, usage):
        with self.lock:
            self.inp += getattr(usage, "input_tokens", 0) or 0
            self.out += getattr(usage, "output_tokens", 0) or 0
            self.calls += 1
    def __enter__(self):
        self.t0 = time.time(); return self
    def __exit__(self, *a):
        cost = None
        if config.PRICE_IN_PER_MTOK is not None and config.PRICE_OUT_PER_MTOK is not None:
            cost = round(self.inp / 1e6 * config.PRICE_IN_PER_MTOK + self.out / 1e6 * config.PRICE_OUT_PER_MTOK, 4)
        append_jsonl(config.RUNS, {"step": self.step, "stage": self.stage, "model": self.model,
                                   "prompt_version": config.PROMPT_VERSION, "date": today(),
                                   "seconds": round(time.time() - self.t0, 1), "calls": self.calls,
                                   "input_tokens": self.inp, "output_tokens": self.out, "est_cost_usd": cost})

def tool_call(model, system, user, schema_cls, meter, max_tokens=4000):
    """Force the model to answer through a tool whose input schema is the pydantic model; validate the result."""
    resp = client().messages.create(
        model=model, max_tokens=max_tokens, system=system,
        tools=[{"name": "submit", "description": "Submit your final answer.", "input_schema": schema_cls.model_json_schema()}],
        tool_choice={"type": "tool", "name": "submit"},
        messages=[{"role": "user", "content": user}])
    meter.add(resp.usage)
    block = next(b for b in resp.content if b.type == "tool_use")
    return schema_cls.model_validate(block.input)

# trace-cdk

A deterministic trace sampler: hash a trace_id, compare the result to a configurable rate, return a boolean. The same trace_id always gets the same answer.

```python
from trace_cdk import TraceSampler

sampler = TraceSampler(rate=0.1)
keep = sampler.should_sample("4a3b2c1d-9f0e")  # -> bool
```

`TraceSampler(rate)` takes a float in `[0.0, 1.0]`. `should_sample(trace_id)` accepts `str`, `int`, or `bytes` and returns `bool`. `rate=0.0` drops everything; `rate=1.0` keeps everything.

## Why

Distributed traces span multiple processes. If each process makes an independent coin flip, a single trace is partially sampled and useless. This library makes the keep/drop decision a pure function of the trace_id, so every participant agrees.

The trade-off: the sampler is stateless and rate-only. It does not adapt to traffic volume, does not prioritise errors, and does not guarantee an exact sample count. If you need adaptive sampling, wrap this behind something that adjusts the rate.

## Edge to know about

`int` and `str` trace IDs are hashed differently — `255` and `"255"` do not match. Pick one representation for a given trace ID and use it everywhere. The library does not try to reconcile them.

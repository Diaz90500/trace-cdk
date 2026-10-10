"""Deterministic trace sampling based on trace_id hashing."""

from __future__ import annotations

import hashlib
from typing import Union


class TraceSampler:
    """Decide whether to keep or drop a trace based on its trace_id.

    The same trace_id always yields the same decision, so that all spans
    belonging to a trace are sampled or dropped together.  The decision
    uses the first 8 bytes of SHA-256(trace_id), interpreted as a big-endian
    unsigned 64-bit integer, compared against ``rate * 2**64``.

    Parameters
    ----------
    rate:
        Sampling fraction in the range ``[0.0, 1.0]``.  ``0.0`` drops
        every trace; ``1.0`` keeps every trace.

    Notes
    -----
    *Strings* are encoded as UTF-8 before hashing, because trace IDs are
    commonly hexadecimal strings.  *Integers* are hashed on their minimal
    big-endian byte representation, which is the natural canonical form.
    This type-awareness avoids a silent collision: the integer ``255`` and
    the string ``"255"`` produce different hashes, as they should.
    Mixing the two representations for the same logical trace ID is a
    caller bug; pick one and stick with it.
    """

    _MASK_64 = (1 << 64) - 1

    def __init__(self, rate: float) -> None:
        if not isinstance(rate, (int, float)):
            raise TypeError("rate must be int or float")
        if rate < 0 or rate > 1:
            raise ValueError("rate must be in [0.0, 1.0]")
        self.rate = float(rate)

    def _hash_to_u64(self, trace_id: Union[str, int, bytes]) -> int:
        """Map a trace_id to a 64-bit bucket in ``[0, 2**64)``."""
        if isinstance(trace_id, str):
            data = trace_id.encode("utf-8")
        elif isinstance(trace_id, int):
            if trace_id < 0:
                raise ValueError("integer trace_id must be non-negative")
            data = trace_id.to_bytes((trace_id.bit_length() + 7) // 8 or 1, "big")
        elif isinstance(trace_id, (bytes, bytearray)):
            data = bytes(trace_id)
        else:
            raise TypeError(
                "trace_id must be str, int, or bytes, got %s" % type(trace_id).__name__
            )
        digest = hashlib.sha256(data).digest()
        return int.from_bytes(digest[:8], "big")

    def should_sample(self, trace_id: Union[str, int, bytes]) -> bool:
        """Return ``True`` if the trace should be kept, ``False`` to drop."""
        bucket = self._hash_to_u64(trace_id)
        threshold = int(self.rate * (1 << 64))
        # ``bucket`` is always in [0, 2**64).  ``threshold`` is in
        # [0, 2**64].  Strict ``<`` makes rate=1.0 keep everything
        # (no bucket is ever == 2**64) and rate=0.0 drop everything.
        return bucket < threshold

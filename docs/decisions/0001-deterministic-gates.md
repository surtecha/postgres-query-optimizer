# Deterministic execution gates

Status: accepted

Models propose candidates as typed data. A separate positive SQL policy controls
execution. Read-only database transactions provide an independent enforcement
layer. Finite result comparisons precede benchmarking. Measured distributions
and an explicit policy decide acceptance.

This rejects some valid PostgreSQL expressions and useful optimizations. The
restricted surface makes the supported behavior reviewable. Finite comparisons
remain evidence for tested snapshots rather than a proof for all possible data.

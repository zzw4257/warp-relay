# Neighbor-exchange input derivation

The example is original PTX written for this project, not copied from a private
research checkout or from an upstream performance benchmark.

- `neighbor_exchange` has two `.u64` parameters. The `ld.param.u64`
  instructions consume both as global pointers. Input declaration parameter 0
  names allocation `input`; parameter 1 names distinct allocation `output`.
- The chosen scenario is exactly `grid_dim=[1,1,1]`,
  `block_dim=[64,1,1]`. `%tid.x` therefore covers 0 through 63.
- Both global arrays must contain at least 64 uint32 elements (256 bytes),
  aligned for uint32 accesses and non-overlapping. No pointer addresses or
  numerical tensor contents are invented.
- Every thread stores one 4-byte value at shared byte offset `4*t` in the
  256-byte `exchange` allocation. It reads at `4*(t xor 32)`.
- For this range, `t xor 32 == (t+32) % 64`. This connects thread 0 to thread 32
  and exchanges the two warps' halves.
- Every thread executes the same straight-line instructions, reaches the
  candidate CTA barriers, and writes one distinct output element. No branch
  override, TMA descriptor, packed parameter, tensor property, pointer table or
  trusted address invariant is needed.
- All six configurable assumptions from the pinned public assumption pool
  are explicitly false. Inherent verifier limitations still apply.

The public input-only audit reported `coverage_complete` on 2026-10-31:

```sh
python3 vendor/sentryward/skills/prepare-kernel-input/scripts/audit_input.py \
  --ptx examples/neighbor_exchange/kernel.ptx \
  --input examples/neighbor_exchange/input.json \
  --output .build/input-audit.json
```

This audit checks ABI coverage; it is separate from real verification. For the
repair experiment, the actual verifier found a shared write/read race between
line 24 (actor 0) and line 28 (actor 32). Adding a barrier before the shared
read produced `race_free`. For the optimization experiment, deleting one of
two consecutive barriers retained `race_free`; deleting the remaining one
produced `potential_race`, and that candidate was rejected.

The mathematical output relation is a specification and a source-level
derivation. A reference equivalence proof and hardware execution have not
been performed. Never substitute this derivation for either check.

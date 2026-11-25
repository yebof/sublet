"""E8's request-level replay (design/sim_spec_ms4.md §7.4; deliverable D35, unit U24).

The engine is fluid: it routes demand rates over warm replica capacity and keeps no request state (design §3.3).
This package replays a request stream through the placements of a fluid run at request level, with in-flight
state, and recomputes the routing, fallback and stranding costs of the run:

  requests  the Azure 2024 conversation week from traces.borrowers.load_requests, cached as uncompressed .npy files
            and memory-mapped by the replay jobs; a Mooncake reader that keeps hash_ids; per-second offsets
  scale     the market scale Gamma of the fluid instance and the copies of the stream at that scale (floor(Gamma)
            copies plus one with probability Gamma - floor(Gamma)), generated per second and never stored
  loop      the service model (128 sequences per replica, a5's TPOT), the placement of a fluid run, the per-second
            loop of the week (own capacity, least-delta site, fallback, stranding at capacity drops) and the
            replica-level loop of the Mooncake hour with and without prefix hits
  fluid     the fluid mode of check E8-2: the replay's accounting fed the demand rates, against the engine

Importing the package loads only numpy and the standard library; the simulator modules are imported inside the
functions that need them.
"""
from .requests import (AZURE_STREAM, BLOCK_TOKENS, MOONCAKE_STREAM, MooncakeTrace, StreamIndex, cache_paths,
                       load_mooncake, open_cache)
from .scale import Copier, MarketScale, market_scale, mooncake_copies
from .loop import (Placement, ReplicaPlan, ServiceModel, placement, replay, replay_replicas, replica_plan,
                   ring_size, service_model, token_costs)
from .fluid import check_e8_2, fluid_mode

__all__ = ["AZURE_STREAM", "BLOCK_TOKENS", "MOONCAKE_STREAM", "MooncakeTrace", "StreamIndex", "cache_paths",
           "load_mooncake", "open_cache", "Copier", "MarketScale", "market_scale", "mooncake_copies", "Placement",
           "ReplicaPlan", "ServiceModel", "placement", "replay", "replay_replicas", "replica_plan", "ring_size",
           "service_model", "token_costs", "check_e8_2", "fluid_mode"]

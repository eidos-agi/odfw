---
okf_version: "0.2"
odfw_version: "0.2.1"
profile: odfw
type: warehouse
odfw_id: odfw:minimal:warehouse
title: "Minimal demo warehouse"
status: implementing
oracle: odfw:minimal:oracle:bronze
layers: [odfw:minimal:layer:bronze]
providers: [odfw:minimal:provider:source]
hosts: [odfw:minimal:host:local]
credential_plane: odfw:minimal:credential-plane:env
authority: [odfw:minimal:authority:readonly]
first_slice: odfw:minimal:slice:demo
proof: [odfw:minimal:acceptance:demo]
non_goals: ["production topology", "real credentials", "customer data"]
verified:
  by: human:daniel
  at: 2026-08-07
  method: "public fixture — no private warehouse content"
  stale_after: 2027-08-07
---

# Minimal demo warehouse

Public fixture for the ODFW validator including fictional sql-packet / check / test / result. **Not** a real warehouse.

Private warehouse packs live in private org repos and are never checked into this format repository.

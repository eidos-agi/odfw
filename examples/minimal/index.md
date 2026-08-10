---
okf_version: "0.2"
odwf_version: "0.2.2"
profile: odwf
type: warehouse
odwf_id: odwf:minimal:warehouse
title: "Minimal demo warehouse"
status: implementing
oracle: odwf:minimal:oracle:bronze
layers: [odwf:minimal:layer:bronze]
providers: [odwf:minimal:provider:source]
hosts: [odwf:minimal:host:local]
credential_plane: odwf:minimal:credential-plane:env
authority: [odwf:minimal:authority:readonly]
first_slice: odwf:minimal:slice:demo
proof: [odwf:minimal:acceptance:demo]
non_goals: ["production topology", "real credentials", "customer data"]
verified:
  by: human:daniel
  at: 2026-08-07
  method: "public fixture — no private warehouse content"
  stale_after: 2027-08-07
---

# Minimal demo warehouse

Public fixture for the ODWF validator including fictional sql-packet / check / test / result. **Not** a real warehouse.

Private warehouse packs live in private org repos and are never checked into this format repository.

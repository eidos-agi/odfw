---
okf_version: "0.2"
odwf_version: "0.2.2"
type: warehouse-concept
odwf_id: odwf:minimal:slice:demo
kind: slice
title: "Demo slice"
includes:
  - odwf:minimal:provider:source
  - odwf:minimal:sql-packet:demo-count
  - odwf:minimal:check:demo
  - odwf:minimal:test:demo
  - odwf:minimal:data-contract:demo
non_goals: ["real data"]
proof: [odwf:minimal:acceptance:demo]
verified:
  by: human:daniel
  at: 2026-08-07
  method: "public fixture"
---

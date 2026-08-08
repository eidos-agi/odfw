---
okf_version: "0.2"
odfw_version: "0.2.1"
type: warehouse-concept
odfw_id: odfw:minimal:slice:demo
kind: slice
title: "Demo slice"
includes:
  - odfw:minimal:provider:source
  - odfw:minimal:sql-packet:demo-count
  - odfw:minimal:check:demo
  - odfw:minimal:test:demo
non_goals: ["real data"]
proof: [odfw:minimal:acceptance:demo]
verified:
  by: human:daniel
  at: 2026-08-07
  method: "public fixture"
---

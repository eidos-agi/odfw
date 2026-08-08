---
okf_version: "0.2"
odfw_version: "0.2.2"
type: warehouse-concept
odfw_id: odfw:minimal:test:demo
kind: test
title: "Demo test"
steps: ["run demo sql-packet", "apply demo check"]
sql_packets: [odfw:minimal:sql-packet:demo-count]
checks: [odfw:minimal:check:demo]
verified:
  by: human:daniel
  at: 2026-08-07
  method: "public fixture"
---

Fictional test procedure.

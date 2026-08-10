---
okf_version: "0.2"
odwf_version: "0.2.2"
type: warehouse-concept
odwf_id: odwf:minimal:test:demo
kind: test
title: "Demo test"
steps: ["run demo sql-packet", "apply demo check"]
sql_packets: [odwf:minimal:sql-packet:demo-count]
checks: [odwf:minimal:check:demo]
verified:
  by: human:daniel
  at: 2026-08-07
  method: "public fixture"
---

Fictional test procedure.

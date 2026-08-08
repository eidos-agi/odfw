---
okf_version: "0.2"
odfw_version: "0.2.1"
type: warehouse-concept
odfw_id: odfw:minimal:check:demo
kind: check
title: "Demo check"
sql_packet: odfw:minimal:sql-packet:demo-count
compare: vector
tolerance:
  mode: absolute
  value: 0
peers: [bronze]
verified:
  by: human:daniel
  at: 2026-08-07
  method: "public fixture"
---

Fictional check.

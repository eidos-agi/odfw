---
okf_version: "0.2"
odwf_version: "0.2.2"
type: warehouse-concept
odwf_id: odwf:minimal:check:demo
kind: check
title: "Demo check"
sql_packet: odwf:minimal:sql-packet:demo-count
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

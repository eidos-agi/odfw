---
okf_version: "0.2"
odwf_version: "0.2.2"
type: warehouse-concept
odwf_id: odwf:minimal:sql-packet:demo-count
kind: sql-packet
title: "Demo count packet"
basis: bronze
sql_path: sql/demo-count.sql
posture: select-only
grain: [demo]
verified:
  by: human:daniel
  at: 2026-08-07
  method: "public fixture"
---

Public fictional SQL packet.

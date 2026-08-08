---
okf_version: "0.2"
odfw_version: "0.2.2"
type: warehouse-concept
odfw_id: odfw:minimal:authority:readonly
kind: authority-boundary
title: "Read only"
allows: ["SELECT"]
denies: ["writes", "DDL"]
network: "private"
verified:
  by: human:daniel
  at: 2026-08-07
  method: "public fixture"
---

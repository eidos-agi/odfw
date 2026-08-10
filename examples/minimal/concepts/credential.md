---
okf_version: "0.2"
odwf_version: "0.2.2"
type: warehouse-concept
odwf_id: odwf:minimal:credential-plane:env
kind: credential-plane
title: "Env file on host"
plane: env-file-on-host
locator: ".env.local on the demo host (never committed)"
forbids: ["print password", "commit .env"]
verified:
  by: human:daniel
  at: 2026-08-07
  method: "public fixture"
---

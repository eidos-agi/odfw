---
okf_version: "0.2"
odwf_version: "0.2.6"
type: warehouse-concept
odwf_id: odwf:minimal:ingestion-contract:source-bounded
kind: ingestion-contract
title: "Bounded demo source ingestion"
provider: odwf:minimal:provider:source
pipeline: odwf:minimal:pipeline:source-load
source_io_paths: [scheduled, reconciliation, manual]
contract_status: enforced
scheduled: true
scheduled_mode: incremental
schedule: "daily"
source_bound: "updated_at in a half-open checkpoint window"
checkpoint_strategy: "advance the durable checkpoint only with the warehouse commit"
overlap_window: "24 hours"
reconciliation_mode: full
reconciliation_schedule: "manual"
reconciliation_strategy: "stage a complete bounded snapshot and compare keys and checksums"
deletion_strategy: "confirm a missing source key twice before tombstoning"
quota_kind: metered
budget_scope: provider
governor_key: "minimal-source-month"
billing_unit: "source transaction"
billing_unit_confidence: reconciled
allowance_units: 1000
hard_limit_units: 800
budget_period: calendar-month
reset_timezone: UTC
estimated_units_per_period: 100
max_units_per_run: 10
governor_mode: enforce
override_policy: "named, expiring approval below the provider allowance"
proof: [odwf:minimal:acceptance:demo]
verified:
  by: human:daniel
  at: 2026-08-10
  method: "public fictional contract for validator coverage"
---

Fictional contract proving that source correctness and source operating bounds are separate gates.

# U-086: review of the final interrupt rerun

Frozen 2026-11-09 before writing the probes. Review scope: #40 comment 189,
approximately one hour, one independently verifiable review result. DSH retains
the card and both acceptance drivers. This session only adds review artifacts;
PR45's host repair remains a separate candidate requiring another reviewer.

Review input is author commit `1e490d074d0b4e91291860d742244af55ed81d88`.
The review branch starts at integration `902b429529f82aad6acc63c6fe4e69c4739ced17`.

- The interrupt exit requires output from the **request being cancelled** before
  cancellation. A reservation, or a prior step's output, is insufficient.
- A successful cancel response must identify the original AU, cancel command,
  step, attempt and model request. `succeeded` and `cancel_accepted` alone do not
  establish that identity.
- Reopening an unresolved step must retain its original reservation as well as
  its identity, status and reason. A reason string is not a reservation check.
- Compare successful Core Work reads from the same run. A failed legacy snapshot
  or a snapshot of another AU cannot establish before/after persistence.
- Count distinct request records separately in each historical run. Report known
  usage on completed requests; absent usage on an unresolved request is unknown.
  Do not treat the sum of known usage as a complete bill or infer remote stoppage.

The offline probes extract only the reviewed assertion/predicate blocks, using
synthetic values and Node vm. They never execute the driver's main, start its
host, access modeld or replay an original request. Successful controls and genuine
counterexample failures are reported separately. Historical evidence stays intact;
there is no artificial GREEN for an uncorrected driver or missing real evidence.

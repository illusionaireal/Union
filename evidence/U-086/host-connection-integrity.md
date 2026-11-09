# Acceptance host: preserve the adopted connection

2026-11-09. Implementation actor: the single codex-home duty session; online
member `c18f0d21-1d63-4e37-af3e-2dbb78d75995`. #40 remains owned by DSH and its
real acceptance is open. Scope and 1–2 hour estimate were read back in comment
182 after fresh board revision 568. This session does not independently approve
its own change.

Base: integration `902b429529f82aad6acc63c6fe4e69c4739ced17`, followed by author
input `096815e44936e1f62a7b680b0d7a5f2db247eb1b` on a separate assistance branch.
The original author history and evidence/127 remain unchanged.

## Problem and repair

`exit22b_host.py` rewrote the connection ID/revision and grant ID/revision supplied
by WorkService. Its mutable `self.grant_ref` could point to a second preparation,
including one for a different AU. Thus the acceptance transport could exercise
a different grant from the one the product actually adopted. It also filled in
missing model and output limits from host defaults.

After freezing the [contract](host-connection-contract.md), six tests exercised
the unchanged host through actual loopback HTTP and a temporary Console restart.
Four test methods failed (ten assertion/subtest failures), while two controls
passed; there were no runtime errors in this corrected RED run. The first test
fixture erroneously used identical synthetic admin/worker tokens and produced
five configuration errors. That run is retained separately and is not a product
RED. Correcting the fixture did not change the host under test.

The host now delegates to the existing product `modeld_factory`, preserving the
supplied connection and the existing 180-second host timeout. It uses the
product's normal polling interval rather than the old host's no-op sleep. No
product runtime, request loop, schema, grant-adoption or transaction code changed.
The misleading claim that this host always used a model double was also corrected.

The new tests verify all transmitted identity/version/model/limit fields; later
grant preparation for another AU; rejection of missing fields before HTTP POST;
Console restart and original-request GET; and rejection of an unavailable
explicit account before grant creation. The six cases plus the three existing
transport HTTP cases pass. [Machine-readable validation](host-connection-verification.json)
records exact source and log hashes and the full-check results.

## Remaining acceptance and adoption

This is a host-wiring repair for independent review, not approval of the author's
whole evidence branch. The page driver still requires successful before/after
Work snapshots, original identity/fact comparison, actual output before cancel,
and settlement/replay assertions described in [review 208903160](https://github.com/illusionaireal/Union/commit/2d15a535a4284e12d497e79770b72c2b5c8b8c44#commitcomment-208903160).
Its duplicate grant preparation and historical claims remain author work; the
repair prevents that second grant from silently replacing the adopted one.

While full tests ran, the author added download evidence at `331a7c1` without
changing this host. A separate [review of that author-only addition](https://github.com/illusionaireal/Union/commit/331a7c1180d119958e54fb43d2821045826544fb#commitcomment-208905473)
reproduced three false-positive download assertions using the exact source in
Node vm; the normal-shape control passed. An error body, null result and another
result were all accepted. The before-restart snapshot was still an error, and
the evidence recorded two model steps/12 checks rather than the README's one/11.
This review does not alter the page driver or its historical records.

The tests invoke only temporary loopback doubles. The real driver main was not
run. Real paid/model calls added: **0**. No NAS service switch, data migration,
new credentials, completed parent card or sustained-operation claim. CI and
another engineering role's review must pass on the actual candidate before
adoption; the implementer does not self-approve.

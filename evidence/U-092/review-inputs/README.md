# U-092 review inputs and reproducibility

This repair responds to Kanban message135: the PR76/77 probes could exit 1
with `ModuleNotFoundError` on clean integration `faa5a4c`, without a report.
That exit was not a reproduction of either product defect. The review source
remains an unpublished snapshot; this change does not publish or adopt it.

Both runners now validate the full 20-file source map before importing the
candidate. Their original behavioral assertions and historical validation
files are unchanged. The [contract](contract.md) separates input diagnosis
from behavioral findings; [tests](../../../tests/test_u092_review_inputs.py)
cover missing inputs, drift before import, and explicit revised manifests.

| Exit | Meaning |
| --- | --- |
| 2 with `input_unavailable`, `input_mismatch` or `input_invalid` | No behavioral tests ran; obtain/correct the selected source input |
| 1 after tests run | Inspect failures/errors in the JSON; an import/runtime error is not a product assertion failure |
| 0 after tests run | Only this bounded synthetic review passed; full CI and independent product adoption remain separate |

The default source is integration `63c4030ec1c520824c00633e42b45019a3e9c533`
plus all 20 files listed in
[lifecycle validation](../duty-review-20261110/validation.json).
The original manifest SHA256 is
`37b49c71de59f9cdad4ab0358a703df6deaa5f980336373a6eea3d8947c30148`.
Those unpublished bytes must be obtained from the original owner. The clean
integration branch contains the review, not those inputs. Neither runner
downloads code, fills in a fixture, or invokes a real model.

For a repaired candidate, obtain its exact commit or isolated source snapshot.
Create a private JSON object with `source_files_sha256`, mapping the same 20
repository-relative paths to SHA256 values of the actual candidate bytes.
Record its exact-byte SHA256 separately. Use the complete current review
package, including `review_inputs.py` and the historical validation file:

```text
python -B evidence/U-092/duty-review-20261110/probes.py <candidate-directory> <private-lifecycle.json> --candidate-manifest <private-manifest.json> --manifest-sha256 <manifest-sha256>
python -B evidence/U-092/superseded-recovery-review/probes.py <candidate-directory> <private-superseded.json> --candidate-manifest <private-manifest.json> --manifest-sha256 <manifest-sha256>
```

The manifest/digest pair is mandatory for revised inputs. An incomplete map,
wrong digest, or later source drift stops before candidate imports. The result
records `source_binding` (historical/revised mode, manifest identity and all 20
actual hashes). This records input identity, not isolation from untrusted code
or verification of every unchanged base/dependency file. Keep private output
outside the candidate and preserve its original files.

Original P1/P2 findings remain open for the implementation owner. #46 owner,
status, WIP and #47/#52 dependencies are unchanged; this repair does not claim
real business acceptance or authorize additional model calls.

Validation history is in [validation.json](validation.json): 5 input tests and
npm check pass; historical probe failures remain 2/3 and 1/3. Two local
817-test full runs exposed validation setup omissions (vendor source, then
Git metadata); those runs remain failed. The SDK and two package tests pass
after setup correction. Final exact-head full-suite and CI receipts belong
on the delivery PR; these partial local runs are not a full-pass claim.

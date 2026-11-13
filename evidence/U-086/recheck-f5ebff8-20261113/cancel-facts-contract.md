# U-086 cancellation fact review contract

Bind review to f5ebff8f80fa06bd7f0520539261576d72758fd8. A local Work step in
`unknown` retains a reservation; it does not establish that modeld reached the
`interrupted` state. Timeout, transport failure, failed execution and absent
reason must not produce `modeld_settlement.interrupted: true` solely from that
local status. Keep the local observation, reason, unknown usage and reservation.
An explicit interrupted observation may remain distinguishable. Used and absent
steps retain their valid behavior, and remote cancellation remains unknown.

Exercise the unchanged candidate helper with synthetic already-read bodies;
perform no product model requests, deployment or mutation. Preserve the original
17 review probes, controls and all failure history. These checks do not supply
missing real modeld receipts or historical snapshots.

# U-092 review evidence index

U-092 / online #46 belongs to the original recovery implementation owner.
These records review an unpublished candidate; they do not adopt that code
or close the recovery card, parent #25, or downstream #47/#52.

- [Lifecycle review](duty-review-20261110/README.md): PR76, two dispatch-after-close
  failures and a normal control on the original 20-file snapshot.
- [Superseded recovery review](superseded-recovery-review/README.md): PR77,
  old recovery replay changes ownership before rejecting; two controls pass.
- [Review input repair](review-inputs/README.md): response to Kanban message135;
  distinguish unavailable or mismatched candidate input from behavioral failure,
  and bind explicitly revised candidates before importing their fixtures.

Original manifests, failure records and product expectations remain intact.
All probes use synthetic HTTP/SQLite data and fake transports. Product repair
requires an exact published candidate, current-head CI and independent review;
no real model request or business acceptance is added by these records.

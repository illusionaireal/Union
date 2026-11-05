# S05 frontend governance owner

- This module owns the React flow and HTTP types for `local_governance.v1`, per `specs/053-union-rewrite/s05-contract.md`. The server owns authorization, effective rules, versions and adoption.
- Render schema 2 actions only from `access.commands`; schema 1 offers the explicit adoption command under its existing stable-principal boundary. Initial governance root and current governor are different facts.
- Bind previews, POSTs and late responses to the original principal, service instance and AU. A renewed session for the same principal does not discard drafts. Cancelling a preflight must prevent POST.
- Persist request identities only, never form contents, passwords or result content. An uncertain write retains its original kind and ID and is resolved by receipt lookup, never automatic replay. Original issuer receipts remain separate from current AU access.
- Use existing React components and styles. Controls have plain Chinese labels, contextual record choices and explicit impact previews. Internal human submissions are not AI execution or autonomous business evidence.
- Strict TDD covers rendered behavior and boundary failures; the coordinated actual-browser check covers the real local HTTP journey and responsive/keyboard conditions. Do not mutate the project ledger, online board or Git from this owner.

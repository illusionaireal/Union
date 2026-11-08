import type { CoreAURead, GovernedAURead, Session } from './types';

export function isGovernedAU(read: CoreAURead): read is GovernedAURead {
  return [2, 3, 4].includes(read.au.schema_version) && 'access' in read;
}

/** Match a server-authorized projection; this does not grant any AU authority. */
export function matchesCoreRead(
  read: CoreAURead,
  session: Session,
  organizationId: string,
): boolean {
  if (
    session.core_protocol !== 'core.au.v1' ||
    !session.principal_id ||
    read.protocol !== 'core.au.v1' ||
    read.au.id !== organizationId ||
    read.au.runtime_profile !== 'core_v1'
  )
    return false;
  if (isGovernedAU(read))
    return (
      read.access.principal_id === session.principal_id &&
      read.access.service_instance === session.service_instance
    );
  return (
    read.au.schema_version === 1 &&
    read.au.governance_root.governor_principal_id === session.principal_id
  );
}

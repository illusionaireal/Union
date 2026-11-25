import { useQuery } from '@tanstack/react-query';
import { api } from '../../api/client';
import type { CoreMaterials } from '../../api/types';
import { WorkScopeLost, type WorkScope } from '../work/useWorkCommand';

export function checkMaterials(read: CoreMaterials, scope: WorkScope) {
  if (read.protocol !== 'core.materials.v1' || read.organization_id !== scope.organizationId ||
      read.access.principal_id !== scope.principalId || !Number.isInteger(read.version) ||
      !Array.isArray(read.materials) || !read.materials.every(item =>
        /^material-[a-f0-9]{32}$/.test(item.id) && typeof item.name === 'string' &&
        item.scope === 'au_read_only' && /^[a-f0-9]{64}$/.test(item.sha256) &&
        Number.isInteger(item.version) && item.version >= 1 && typeof item.read_allowed === 'boolean'))
    throw new WorkScopeLost('资料读取与当前主体或组织不匹配');
  return read;
}

export function useMaterials(scope: WorkScope) {
  return useQuery({
    queryKey: ['core-materials', scope.organizationId, scope.principalId, scope.serviceInstance],
    queryFn: async ({ signal }) => checkMaterials(await api.coreMaterials(scope.organizationId, signal), scope),
    retry: false,
  });
}

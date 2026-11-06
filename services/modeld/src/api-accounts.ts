import { identifier, requireValue } from './journal';
import { CredentialContent } from './credential-content';

export interface APIRegistration {
  id: string; au_id: string; principal_id: string; name: string;
  base_url: string; api_key: string; model_id: string;
  wire_api?: 'chat_completions' | 'responses';
  reasoning_effort?: 'none' | 'minimal' | 'low' | 'medium' | 'high' | 'xhigh' | 'max';
}
export interface APIConnectionReceipt {
  id: string; au_id: string; principal_id: string; name: string;
  profile: 'openai_compatible' | 'openai_responses'; model_id: string; grant_ref: string; grant_revision: number;
  wire_api?: APIRegistration['wire_api']; reasoning_effort?: APIRegistration['reasoning_effort'];
}
/** Private modeld input. Never return this object over an HTTP endpoint. */
export interface APIAccount extends APIRegistration {
  account_ref: string; grant_ref: string; grant_revision: number;
}

export function uuid(value: unknown): asserts value is string {
  requireValue(typeof value === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value), 'invalid_uuid');
}
export function validateAPIRegistration(value: unknown): APIRegistration {
  const required = ['api_key','au_id','base_url','id','model_id','name','principal_id'];
  requireValue(value && typeof value === 'object' && !Array.isArray(value) && required.every(k => Object.hasOwn(value, k)) &&
    Object.keys(value).every(k => [...required, 'wire_api', 'reasoning_effort'].includes(k)), 'invalid_api_connection_fields');
  const input = value as APIRegistration;
  if (Object.hasOwn(input, 'wire_api')) requireValue(['chat_completions','responses'].includes(input.wire_api!), 'unsupported_wire_api');
  if (Object.hasOwn(input, 'reasoning_effort')) requireValue(input.wire_api === 'responses' &&
    ['none','minimal','low','medium','high','xhigh','max'].includes(input.reasoning_effort!), 'unsupported_reasoning_effort');
  identifier(input.id); identifier(input.au_id); uuid(input.principal_id);
  for (const [field, limit] of [['name', 160], ['model_id', 256], ['base_url', 2048]] as const)
    requireValue(typeof input[field] === 'string' && input[field].length > 0 && input[field].length <= limit &&
      input[field].trim() === input[field] && !/[\x00-\x1f\x7f]/.test(input[field]), 'invalid_api_connection_' + field);
  requireValue(typeof input.api_key === 'string' && /^[\x21-\x7e]{1,4096}$/.test(input.api_key), 'invalid_api_key');
  let url: URL | undefined;
  try { url = new URL(input.base_url); } catch { /* fail with a secret-free validation error */ }
  requireValue(url && !url.username && !url.password && !url.search && !url.hash &&
    !input.base_url.includes('?') && !input.base_url.includes('#') &&
    (url.protocol === 'https:' || url.protocol === 'http:' &&
      (url.hostname === 'localhost' || url.hostname === '[::1]' || /^127(?:\.\d{1,3}){3}$/.test(url.hostname))),
    'invalid_api_connection_base_url');
  // Even user-supplied labels/model names must not echo the private credential.
  requireValue(!new CredentialContent(input.api_key).contains({ ...input, api_key: undefined }), 'credential_in_api_connection_metadata');
  return input;
}

import type { CoreAURead } from '../../api/types';
import type { GovernanceScope } from '../governance/model';

export const modelKinds = [
  'save_connection',
  'reconcile_connection',
  'set_connection',
  'grant_model_resources',
  'start_model_check',
  'reconcile_model_check',
  'cancel_model_check',
] as const;
export type ModelKind = (typeof modelKinds)[number];
export type ModelProfile = 'openai_compatible' | 'modeld_grant' | 'openai_responses';
export type CapabilityStatus = 'verified_real' | 'controlled' | 'unsupported';
export type ProfileCapability =
  | 'text_answer'
  | 'tool_roundtrip'
  | 'usage_reporting'
  | 'streaming'
  | 'long_job_new_input'
  | 'cancel_and_query';
export interface CapabilityClaim {
  status: CapabilityStatus;
  note: string;
  evidence?: string;
}
export interface ProfileScope {
  title: string;
  auth: 'api_key' | 'grant';
  capabilities: Record<ProfileCapability, CapabilityClaim>;
}
export interface CoreConnection {
  id: string;
  revision: number;
  name: string;
  profile: ModelProfile;
  model: string;
  base_url?: string;
  max_output_tokens: number;
  grant_ref: string;
  grant_revision: number;
  enabled: boolean;
  is_default: boolean;
  last_check: { check_id: string; revision: number; profile: ModelProfile; at: number } | null;
}
export interface ModelUsage {
  input_tokens: number | null;
  output_tokens: number | null;
  cached_input_tokens: number | null;
  cache_write_tokens: number | null;
  reasoning_tokens: number | null;
  cost_minor: number | null;
  currency: string | null;
  cost_status: string;
  cost_basis?: string;
  source?: string;
  basis?: 'result' | 'events' | 'unknown';
  observed_through_seq?: number | null;
}
export interface ModelDiagnostic {
  code: string;
  next_step: string;
}
export interface ModelAttempt {
  id: string;
  stage: number;
  state: string;
  purpose: 'connection_check';
  usage: ModelUsage;
  diagnostic?: ModelDiagnostic | null;
}
export type ModelEvent = { seq: number } & (
  { type: 'text_delta'; text: string } | { type: 'tool_call_complete'; name: 'read_document' }
);
export interface ModelEvents {
  protocol: 'core.model-events.v1';
  organization_id: string;
  check_id: string;
  attempt_id: string;
  access: { principal_id: string; service_instance: string };
  version: number;
  source: 'persisted_modeld_events';
  state: string;
  events: ModelEvent[];
  cursor: number;
  last_seq: number;
  has_more: boolean;
  events_complete: boolean;
  truncated: boolean;
}
export interface ModelCheck {
  id: string;
  principal_id: string;
  member_id: string;
  binding_id: string;
  binding_version: number;
  work_id: string;
  work_version: number;
  mandate_id: string;
  mandate_version: number;
  agent_definition: { id: string; version: number; tools: string[] };
  connection_id: string;
  connection_revision: number;
  resource_revision: number;
  status:
    'queued' | 'running' | 'unknown' | 'not_adopted' | 'failed' | 'succeeded' | 'cancel_requested';
  stage: number;
  stop_requested: boolean;
  output: string | null;
  document_name: string;
  message: string;
  diagnostic?: ModelDiagnostic | null;
  attempts: ModelAttempt[];
  waiting: {
    object: string;
    condition: string;
    responsible_member_id: string;
    scope: string;
  } | null;
}
export interface ModelOperation {
  id: string;
  status: 'saving' | 'succeeded' | 'rejected' | 'unknown';
  message: string;
  diagnostic?: ModelDiagnostic | null;
}
export interface ModelRead {
  protocol: 'core.models.v1';
  organization_id: string;
  version: number;
  access: { principal_id: string; service_instance: string; can_configure: boolean };
  governance_status: string;
  document_read_allowed: boolean;
  capabilities: {
    profiles: ModelProfile[];
    tools: string[];
    profile_scope: Record<string, ProfileScope>;
    autonomous_business: false;
  };
  connections: CoreConnection[];
  operations: ModelOperation[];
  checks: ModelCheck[];
  resources: {
    grant: {
      max_calls: number;
      allow_unknown_cost: boolean;
      reason: string;
      revision: number;
    } | null;
    reserved_calls: number;
    plan_max_calls: number;
  };
}
export interface ModelRequest {
  id: string;
  organization_id: string;
  base_version: number;
  kind: ModelKind;
  data: Record<string, unknown>;
}
export interface ModelReceipt extends Omit<ModelRequest, 'data'> {
  version: number;
  actor_principal_id: string;
  status: 'succeeded' | 'rejected';
  effect: string;
  message: string;
  created_at: string;
  operation_id?: string;
  check_id?: string;
}
export interface ModelReference extends Omit<ModelRequest, 'data'> {
  principal_id: string;
  service_instance: string;
  resolved: boolean;
  target: string;
}
export interface ModelDraft {
  key: string;
  kind: ModelKind;
  read: ModelRead;
  core: CoreAURead;
  scope: GovernanceScope;
  connection?: CoreConnection;
  check?: ModelCheck;
  operation?: ModelOperation;
  enabled?: boolean;
  makeDefault?: boolean;
}

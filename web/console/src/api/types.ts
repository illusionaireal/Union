/** Wire contracts of ai_union.console / observation. No host paths or credentials. */
import type { GovernanceAUFields, GovernanceReadFields } from '../features/governance/types';
export type CommandKind =
  | 'create'
  | 'create_v1'
  | 'start'
  | 'pause'
  | 'event'
  | 'resources'
  | 'model'
  | 'amend'
  | 'reconcile'
  | 'api_connection'
  | 'api_binding'
  | 'api_test'
  | 'api_import'
  | 'api_cost_allocate'
  | 'company_usage';
export type ReceiptKind =
  CommandKind | 'api_connection' | 'api_binding' | 'api_test' | 'company_usage';
export interface Session {
  core_protocol?: 'core.au.v1';
  principal_id?: string | null;
  session_scope?: string;
  role: 'board' | 'observer' | 'core';
  platform_admin?: boolean;
  organizations: { id: string; name: string; profile?: 'legacy_v0' | 'core_v1' }[];
  service_instance: string;
  executors: ('fixture' | 'codex' | 'api')[];
}
export interface CoreAUBase {
  id: string;
  name: string;
  goal: string;
  board_name: string;
  version: number;
  charter_version: number;
  policy_version: number;
  runtime_profile: 'core_v1';
  autonomy_state: 'inactive';
  resource_state: 'planned';
  governance_root: { creator_principal_id: string; governor_principal_id: string };
  charter: Charter;
  resources: Pick<Resources, 'max_calls' | 'timeout_seconds'>;
}
export interface PreparedAURead {
  protocol: 'core.au.v1';
  au: CoreAUBase & {
    version: 0;
    charter_version: 1;
    policy_version: 0;
    schema_version: 1;
  };
  capabilities: { read: true; autonomous_business: false; charter_enforcement: 'not_activated' };
}
export interface GovernedAURead extends GovernanceReadFields {
  protocol: 'core.au.v1';
  au: CoreAUBase & GovernanceAUFields;
}
export type CoreAURead = PreparedAURead | GovernedAURead;
export interface ModelConnection {
  key_source?: string | null;
  catalog?: {context_window?:number; tool_call?:boolean; input_modalities?:string[]; revision?:string; cost?:{input?:number;output?:number}} | null;
  gateway_ref?: { id: string; revision: number };
  id: string;
  revision: number;
  has_api_key: boolean;
  updated_at: string;
  config: {
    version?: 2;
    backend?: 'modeld';
    grant_ref?: string | null;
    grant_revision?: number | null;
    deadlines?: { first_event_ms: number; idle_ms: number; task_ms: number | null };
    provider?: string;
    protocol?: string;
    api_key_env?: string;
    api_key_file?: string;
    auth_type?: 'key' | 'none';
    allow_private_http?: boolean;
    context_policy?: {strategy?:'trim_history'|'reject';window?:number};
    billing?: {basis: 'metered' | 'subscription' | 'owned' | 'unknown'; currency?: string; revision?: string; input_per_million_minor?: number; output_per_million_minor?: number;cache_read_per_million_minor?:number};
    name: string;
    base_url?: string;
    model: string;
    response_format?: 'agent' | 'json_schema' | 'json_object';
    token_limit_field?: 'max_completion_tokens' | 'max_tokens';
    max_output_tokens: number;
    timeout_seconds?: number;
    enabled: boolean;
  };
}
export interface Charter {
  text: string;
  allowed_operations: string[];
  allowed_tools: string[];
  reserved_matters: string[];
  board_can_amend: boolean;
}
export interface Resources {
  max_calls: number;
  timeout_seconds: number;
  max_cost?: number;
}
export interface Member {
  id: string;
  name: string;
}
export interface Position {
  id: string;
  title: string;
  mandate: string;
  version: number;
}
export interface Assignment {
  id: string;
  member_id: string;
  position_id: string;
  active: boolean;
}
export interface Work {
  id: string;
  title: string;
  instruction: string;
  member_id: string;
  assignment_id: string;
  version: number;
  status: string;
  display_status: string;
  dependencies: string[];
  artifact_ids: string[];
  run_id?: string;
  summary?: string;
}
export interface Artifact {
  id: string;
  name: string;
  version: number;
  sha256: string;
  work_id: string;
  run_id: string;
  member_id: string;
  created_at: string;
}
export interface ArtifactContent extends Artifact {
  content: string;
  verified: boolean;
}
export interface ExecutionFailure {
  code: string;
  message: string;
  recovery: string;
  http_status?: number;
  parameter?: string;
  rule?: string;
}
export interface Run {
  execution?: { connection_id?: string; protocol?: string; transport_source?: string };
  id: string;
  kind: string;
  work_id: string | null;
  executor: string;
  status: string;
  display_status: string;
  started_at: string;
  ended_at: string | null;
  usage: { input_tokens?: number; output_tokens?: number; cost_basis?:string; cost_minor?:number|null; cost_status?:string; currency?:string|null; context?:{dropped_messages?:number;estimated_input_tokens?:number} } | null;
  member_id: string;
  simulated: boolean;
  host_confirmed: boolean;
  failure?: ExecutionFailure;
}
export interface RuntimeSummary {
  runtime_id: string | null;
  name: string;
  mode: 'embedded' | 'managed_local' | 'external' | 'unregistered';
  instance_id: string | null;
  observed_at: string | null;
  liveness: 'confirmed' | 'unconfirmed' | 'unknown';
  dispatch_state: string;
  active_run_id: string | null;
  capabilities: string[];
}
export interface MemberExecution {
  member_id: string;
  assignment_ids: string[];
  current_work_id: string | null;
  work_state: 'executing' | 'ready' | 'waiting' | 'blocked' | 'idle';
  reason_codes: string[];
  recent_run: Pick<Run, 'id' | 'status' | 'display_status' | 'started_at' | 'ended_at' | 'work_id'> | null;
  session: { id: string | null; updated_at: string | null; has_checkpoint: boolean | null; resume_state: string };
  workspace: { mode: 'virtual_only' | 'shared_business'; revision: number | null; available: boolean; reason_codes: string[] };
}
export interface OrganizationEvent {
  id: string;
  kind: string;
  created_at: string;
  consumed: number;
  data: Record<string, unknown>;
}
export interface Decision {
  id: string;
  actor: string;
  status: string;
  created_at: string;
  data: { issue: string; rationale?: string; operations: unknown[]; [key: string]: unknown };
}
export interface Receipt {
  id: string;
  organization_id: string | null;
  base_version: number | null;
  kind: ReceiptKind;
  actor: string;
  created_at: string;
  ended_at?: string;
  status: 'accepted' | 'succeeded' | 'rejected' | 'unknown' | 'blocked' | 'failed';
  message: string;
  requested_model?: string | null;
  failure?: ExecutionFailure;
}
export interface CommandRequest {
  id: string;
  kind: CommandKind;
  organization_id: string | null;
  base_version: number | null;
  data: Record<string, unknown>;
}
export interface PendingRequest {
  id: string;
  organization_id: string | null;
  kind: ReceiptKind;
}
export interface Snapshot {
  bootstrap?: {
    members: { name: string; role: string; mandate: string }[];
    tasks: { title: string; instruction: string; owner: string; dependencies?: string[] }[];
    coordinator?: string;
    strategy?: string;
    updated_at: string;
  } | null;
  company?: Company | null;
  service_instance: string;
  snapshot_sequence: number;
  organization: {
    id: string;
    name: string;
    goal: string;
    version: number;
    charter_version: number;
    policy_version: number;
    phase: string;
    members: Record<string, Member>;
    positions: Record<string, Position>;
    assignments: Record<string, Assignment>;
    work: Record<string, Work>;
    artifacts: Record<string, Artifact>;
    resources: Resources;
  };
  charter: Charter;
  budget: {
    calls_reserved: number;
    max_calls: number;
    blocked_reason: string | null;
    cost_status: string;
  };
  ready_work: string[];
  execution_config: { codex_model: string | null; api_connection_id?: string | null; roles?: Record<string,{connection_id:string;fallbacks?:string[]}>; fallbacks?:string[] };
  pending_events: number;
  next_step: string;
  blocked_reasons: string[];
  next_review_at: string | null;
  collected_at: string;
  execution_state: string;
  dispatch_state: string;
  host_activity: { confirmed: boolean; owner?: string };
  runtime: RuntimeSummary;
  member_execution: MemberExecution[];
  runs: Run[];
  events: OrganizationEvent[];
  decisions: Decision[];
  receipts: Receipt[];
  pagination: { offset: number; limit: number; event_count: number; decision_count: number };
  source: 'fixture' | 'real' | 'mixed' | 'not_run';
}

export interface Company {
  kind: 'novel';
  currency: string;
  book_title: string | null;
  target_cycles: number;
  completed: boolean;
  scope: string;
  quality_review: string;
  chapters: {
    chapter_number: number;
    title: string;
    artifact_id: string;
    feedback: string;
    subscriptions: number;
    income_minor: number;
    negative_feedback: boolean;
  }[];
  reviews: {
    chapter_number: number;
    response: string;
    decision_id: string;
    next_work_ids: string[];
  }[];
  feedback_actions: {
    chapter_number: number;
    response: string;
    decision_id: string;
    next_work_ids: string[];
    delivered_work_ids: string[];
  }[];
  totals: {
    initial_budget_minor: number;
    balance_minor: number;
    income_minor: number;
    operating_cost_minor: number;
    model_estimate_minor: number;
    unknown_model_costs: number;
  };
  ledger: {
    id: string;
    kind: string;
    amount_minor: number | null;
    source: string;
    reference: string;
    input_tokens?: number | null;
    output_tokens?: number | null;
  }[];
}

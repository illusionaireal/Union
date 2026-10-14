/** Wire contracts of ai_union.console / observation. No host paths or credentials. */
export type CommandKind =
  'create' | 'start' | 'pause' | 'event' | 'resources' | 'model' | 'amend' | 'reconcile';
export interface Session {
  role: 'board' | 'observer';
  organizations: { id: string; name: string }[];
  service_instance: string;
  executors: ('fixture' | 'codex')[];
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
export interface Run {
  id: string;
  kind: string;
  work_id: string | null;
  executor: string;
  status: string;
  display_status: string;
  started_at: string;
  ended_at: string | null;
  usage: { input_tokens?: number; output_tokens?: number } | null;
  member_id: string;
  simulated: boolean;
  host_confirmed: boolean;
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
  kind: CommandKind;
  actor: string;
  created_at: string;
  ended_at?: string;
  status: 'accepted' | 'succeeded' | 'rejected' | 'unknown';
  message: string;
  requested_model?: string | null;
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
  kind: CommandKind;
}
export interface Snapshot {
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
  execution_config: { codex_model: string | null };
  pending_events: number;
  next_step: string;
  blocked_reasons: string[];
  next_review_at: string | null;
  collected_at: string;
  execution_state: string;
  dispatch_state: string;
  host_activity: { confirmed: boolean; owner?: string };
  runs: Run[];
  events: OrganizationEvent[];
  decisions: Decision[];
  receipts: Receipt[];
  pagination: { offset: number; limit: number; event_count: number; decision_count: number };
  source: 'fixture' | 'real' | 'mixed' | 'not_run';
}

export const governanceKinds = [
  'adopt_governance',
  'configure_governance',
  'acknowledge_recovery',
  'activate_governance',
  'renew_governance',
  'nominate_governor',
  'accept_governance',
  'recover_governance',
  'exit_governance',
  'amend_charter',
  'set_goal',
  'appoint',
  'update_appointment',
  'create_work',
  'update_work',
  'grant_mandate',
  'revoke_mandate',
  'handoff_responsibility',
  'begin_local_action',
  'submit_local_result',
  'accept_local_result',
] as const;
export type GovernanceKind = (typeof governanceKinds)[number];
export interface GovernanceConfig {
  profile: 'local_governance.v1';
  final_decision_principal_id: string;
  reserved_matters: string[];
  unavailability: {
    mode: 'exit_after_timeout' | 'successor_after_timeout';
    timeout_seconds: number;
    successor_principal_id?: string;
  };
}
export interface GovernanceState extends GovernanceConfig {
  status: 'prepared' | 'active' | 'exited';
  current_principal_id: string;
  valid_until: number | null;
  recovery_ack: { principal_id: string; policy_version: number } | null;
  nomination: { principal_id: string; policy_version: number; reason: string } | null;
}
export interface ResponsibilityMember {
  id: string;
  name: string;
  kind: 'human';
  principal_id: string;
}
export interface ResponsibilityBinding {
  id: string;
  member_id: string;
  duty: string;
  version: number;
  active: boolean;
}
export interface ResponsibilityWork {
  id: string;
  title: string;
  instruction: string;
  responsible_binding_id: string;
  version: number;
  status: 'open' | 'stopped' | 'delivered' | 'needs_review';
  history: Array<{ from_binding_id: string; to_binding_id: string; reason: string }>;
  result_ids: string[];
}
export interface ResponsibilityMandate {
  id: string;
  work_id: string;
  binding_id: string;
  binding_version: number;
  work_version: number;
  goal_version: number;
  charter_version: number;
  policy_version: number;
  parent_id: string | null;
  actions: ['record_memory'];
  can_delegate: boolean;
  version: number;
  active: boolean;
  issuer_principal_id: string;
}
export interface LocalAttempt {
  id: string;
  kind: 'local_submission';
  work_id: string;
  principal_id: string;
  member_id: string;
  binding_id: string;
  binding_version: number;
  work_version: number;
  charter_version: number;
  policy_version: number;
  goal_version: number;
  mandates: Array<{ id: string; version: number }>;
  status: 'open' | 'submitted' | 'not_adopted' | 'accepted';
  content?: string;
  sha256?: string;
  authority_reason?: string;
}
export interface InternalResult {
  id: string;
  work_id: string;
  attempt_id: string;
  content: string;
  sha256: string;
  accepted_by: string;
  author_member_id: string;
  created_at: string;
}
export interface GovernanceAUFields {
  schema_version: 2;
  goal_version: number;
  governance: GovernanceState;
  members: Record<string, ResponsibilityMember>;
  bindings: Record<string, ResponsibilityBinding>;
  work: Record<string, ResponsibilityWork>;
  mandates: Record<string, ResponsibilityMandate>;
  attempts: Record<string, LocalAttempt>;
  results: Record<string, InternalResult>;
}
export interface GovernanceReadFields {
  access: {
    principal_id: string;
    service_instance: string;
    role: 'governor' | 'member' | 'successor' | 'nominee';
    commands: GovernanceKind[];
  };
  governance_status: 'prepared' | 'active' | 'unavailable' | 'exited';
  readiness_gaps: string[];
  history: Array<{
    version: number;
    command_id: string;
    kind: GovernanceKind;
    principal_id: string;
    reason: string;
    created_at: string;
    prior_policy_version: number;
  }>;
  capabilities: {
    read: true;
    local_governance: true;
    local_submission: boolean;
    autonomous_business: false;
    charter_enforcement: 'supported_local_rules';
    supported_operations: ['record_memory'];
    unavailable: string[];
  };
}
export interface GovernanceRequest {
  id: string;
  organization_id: string;
  base_version: number;
  kind: GovernanceKind;
  data: Record<string, unknown>;
}
export interface GovernanceReceipt {
  id: string;
  organization_id: string;
  base_version: number;
  kind: GovernanceKind;
  actor_principal_id: string;
  created_at: string;
  status: 'succeeded' | 'rejected';
  message: string;
  version: number;
  effect?: 'applied' | 'none' | 'evidence_only';
}

import type { CoreWorkItem, WorkIntent, WorkIntentStatus } from '../../api/types';
import { ResultList } from './ResultList';
import { useWorkCommand, type WorkScope } from './useWorkCommand';

const states: Record<WorkIntentStatus, string> = {
  accepted: '工作意图已接受',
  running: '正在推进',
  waiting_unknown: '执行结果待核对',
  awaiting_decision: '等待治理决定',
  blocked: '工作受阻',
  delivered: '已交付',
  stopped: '已停止后续推进',
};

type Props = {
  scope: WorkScope;
  work: CoreWorkItem;
  intent: WorkIntent;
  version: number;
  canManage: boolean;
  onAccessLost: () => void;
};

function eligibleCandidate(work: CoreWorkItem, principal: string) {
  const { intent } = work;
  if (intent?.status !== 'awaiting_decision' || intent.delivery_mode !== 'governor_review' ||
      intent.decision?.authorized_principal_id !== principal) return;
  const decision = intent.decision;
  if ((work.input_seq ?? 0) !== decision.input_cursor) return;
  const result = work.results.find(r => r.id === decision.result_id && r.seq === decision.result_seq &&
    r.sha256 === decision.sha256 && r.status === 'candidate');
  if (result) return { decision, result };
}

function canStop(intent: WorkIntent) {
  return ['accepted', 'running', 'waiting_unknown', 'awaiting_decision', 'blocked'].includes(intent.status);
}

function IntentActions({ scope, work, intent, version, canManage, onAccessLost }: Props) {
  const identifiers = { workId: work.id, intentId: intent.id };
  const approve = useWorkCommand(scope, onAccessLost, { kind: 'decide_work_intent', ...identifiers });
  const stop = useWorkCommand(scope, onAccessLost, { kind: 'stop_work_intent', ...identifiers });
  const candidate = canManage ? eligibleCandidate(work, scope.principalId) : undefined;
  const stopAllowed = canManage && canStop(intent);
  const busy = approve.sending || approve.checking || stop.sending || stop.checking;
  const sameIntent = (row: CoreWorkItem) => row.id === work.id && row.intent?.id === intent.id;

  async function decide() {
    if (busy || !candidate) return;
    const { result_id, result_seq, sha256, input_cursor } = candidate.decision;
    await approve.send({
      work_id: work.id, intent_id: intent.id, result_id, result_seq, sha256, input_cursor,
      reason: '治理者明确批准采用并交付此候选成果',
    }, version, async read => {
      const row = read.works.find(sameIntent);
      const current = row && eligibleCandidate(row, scope.principalId)?.decision;
      if (!current || current.result_id !== result_id || current.result_seq !== result_seq ||
          current.sha256 !== sha256 || current.input_cursor !== input_cursor)
        throw new Error('待决定的候选成果或输入覆盖已变化，请刷新核对。');
    });
  }

  async function stopWork() {
    if (busy || !stopAllowed) return;
    await stop.send({ work_id: work.id, intent_id: intent.id, reason: '治理者要求停止这项工作后续推进' },
      version, async read => {
        const current = read.works.find(sameIntent)?.intent;
        if (!current || !canStop(current)) throw new Error('工作状态已变化，请刷新核对。');
      });
  }

  return <>
    {candidate && !approve.reference && <div>
      <p>待决定成果：{candidate.result.title} · 版本 {candidate.result.seq} · 覆盖输入至序号 {candidate.decision.input_cursor}</p>
      <button className="button primary" type="button" disabled={busy || approve.blocked} onClick={() => void decide()}>
        批准并交付此成果
      </button>
    </div>}
    {intent.status === 'awaiting_decision' && intent.decision && (work.input_seq ?? 0) > intent.decision.input_cursor &&
      <p>已有更新的补充输入。请等待工作纳入后重新形成候选。</p>}
    {intent.status === 'awaiting_decision' && intent.decision &&
      (!canManage || intent.decision.authorized_principal_id !== scope.principalId) &&
      <p>当前身份不能批准此候选，等待有权治理者处理。</p>}
    {stopAllowed && !stop.reference && <div>
      <p>停止后续推进。已派发而结果未知的请求会保留待核对。</p>
      <button className="button secondary" type="button" disabled={busy || stop.blocked} onClick={() => void stopWork()}>
        停止工作
      </button>
    </div>}
    <ActionReceipt command={approve} label="批准交付" retry={!!candidate} busy={busy} />
    <ActionReceipt command={stop} label="停止工作" retry={stopAllowed} busy={busy} />
  </>;
}

function ActionReceipt({ command, label, retry, busy }: {
  command: ReturnType<typeof useWorkCommand>; label: string; retry: boolean; busy: boolean;
}) {
  return <>
    {command.reference && <div>
      {!command.reference.resolved && <p>{label}的原请求已保留，请查询原回执。</p>}
      <button className="button secondary" type="button" disabled={busy} onClick={() => void command.lookup()}>
        查询{label}的原请求
      </button>
      {retry && command.reference.outcome === 'rejected' &&
        <button className="button secondary" type="button" disabled={busy} onClick={command.another}>重新核对{label}</button>}
    </div>}
    {command.note && <p role="status">{command.note}</p>}
  </>;
}

export function WorkIntentProgress(props: Props) {
  const { scope, work, intent } = props;
  return <section aria-label="持久工作进度">
    <p role="status">{states[intent.status] ?? '工作状态待核对'}</p>
    {intent.reason && <p>{intent.reason}</p>}
    <p>{intent.delivery_mode === 'automatic_text' ? '自动交付文本' : '由治理者审查后交付'} · {work.budget.used} 已用 · {work.budget.reserved} 已预约</p>
    {!!work.results.length && <ResultList organizationId={scope.organizationId} works={[work]} />}
    <IntentActions key={intent.id} {...props} />
  </section>;
}

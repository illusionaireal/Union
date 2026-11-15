// Keep the three separate cancellation facts apart: what the product accepted locally, how
// the supervised Work step settled locally, and what this machine cannot ever prove - whether
// the remote model service stopped. A local Work step in `unknown` is NOT a modeld receipt:
// Core can leave it unknown because of a wait timeout, a transport failure or a failed
// execution, so `interrupted` stays unknown unless an explicit validated receipt is supplied.
// Read-only: every input is an already-read body.
const PROTOCOL = 'acceptance.cancel-facts.v1';

const MODELD_UNAVAILABLE_REASON =
  '本机 Work step 状态不是 modeld 回执：等待超时、传输失败或执行失败都会留下 unknown，不能据此推断 modeld interrupted';

function buildCancelFacts({ receipt, step, work, modeldReceipt = null }) {
  const accepted = Boolean(receipt && receipt.cancel_accepted === true);
  const budget = (work && work.budget) || {};
  const observed = Boolean(step);
  const explicitInterrupted = Boolean(modeldReceipt && modeldReceipt.status === 'interrupted');
  const modeldSource = explicitInterrupted ? 'explicit_receipt'
    : (observed && step.status === 'used' ? 'local_work_step' : 'unavailable');
  // Only an explicit receipt can assert an interruption. A completed call may assert that it
  // was not interrupted; a local unknown or an absent step stays unknown rather than false.
  const interrupted = explicitInterrupted ? true
    : (observed && step.status === 'used' ? false : null);
  return {
    protocol: PROTOCOL,
    local_acceptance: {
      accepted,
      receipt_id: (receipt && receipt.id) || null,
      status: (receipt && receipt.status) || null,
      delivery_message: (receipt && receipt.message) || null,
    },
    modeld_settlement: {
      observed,
      step_status: observed ? step.status : null,
      interrupted,
      reason: observed ? (step.reason ?? null) : null,
      usage: observed ? (step.usage ?? null) : null,
      cost_status: observed ? (step.cost_status || null) : null,
      // Where the interrupted answer comes from, so a reader cannot mistake a local Work
      // step for modeld evidence.
      modeld_source: modeldSource,
      modeld_receipt_id: explicitInterrupted ? (modeldReceipt.model_request_id || null) : null,
      modeld_unavailable_reason: modeldSource === 'explicit_receipt' ? null : MODELD_UNAVAILABLE_REASON,
    },
    // A local acceptance and a durable delivery observation never prove the remote side
    // stopped, so this stays unknown unless someone supplies the remote's own record.
    remote_fact: {
      status: 'unknown',
      reason: '本机取消受理与投递观察不证明远端模型服务已停止；远端事实需由远端自身记录确认',
    },
    reservation: {
      reserved: Number.isSafeInteger(budget.reserved) ? budget.reserved : null,
      used: Number.isSafeInteger(budget.used) ? budget.used : null,
      max_calls: Number.isSafeInteger(budget.max_calls) ? budget.max_calls : null,
    },
  };
}

module.exports = { buildCancelFacts };

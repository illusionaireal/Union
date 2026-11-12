// Keep the three separate cancellation facts apart: what the product accepted locally,
// how the supervised step actually settled, and what this machine cannot ever prove -
// whether the remote model service stopped. Read-only: the inputs are already-read bodies.
const PROTOCOL = 'acceptance.cancel-facts.v1';

function buildCancelFacts({ receipt, step, work }) {
  const accepted = Boolean(receipt && receipt.cancel_accepted === true);
  const budget = (work && work.budget) || {};
  const observed = Boolean(step);
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
      // Only an explicit unknown settlement that carries a reason counts as interrupted.
      interrupted: observed ? step.status === 'unknown' : null,
      reason: observed ? (step.reason || null) : null,
      usage: observed ? (step.usage ?? null) : null,
      cost_status: observed ? (step.cost_status || null) : null,
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

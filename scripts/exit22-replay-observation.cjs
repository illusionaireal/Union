// Record whether reopening the original work dispatched anything new.
// Read-only: both inputs are already-read core.work.v1 bodies; no request is issued here.
const { observeNoNewDispatch } = require('./exit22-restart-evidence.cjs');

const PROTOCOL = 'acceptance.replay-observation.v1';

function write(fs, path, output, value) {
  fs.writeFileSync(path.join(output, 'replay-observation.json'), JSON.stringify(value, null, 2));
}

function recordReplayObservation({ fs, path, output, before, after, workId, check }) {
  let observation;
  try {
    observation = observeNoNewDispatch(before, after, workId);
  } catch (error) {
    const reason = String((error && error.message) || error);
    write(fs, path, output, { protocol: PROTOCOL, status: 'failed', work_id: workId, reason, new_dispatches: null });
    check('no new dispatch after reopening the original work (' + reason + ')', false);
    return { status: 'failed', reason };
  }
  write(fs, path, output, observation);
  // Only an explicit dispatch counter may claim zero new dispatches. Unchanged
  // persisted state (status 'unchanged') proves the Work did not change, not that
  // reopening issued no request, so it adds no passing check here.
  if (observation.status === 'observed' && observation.dispatch_count === 0) {
    check('no new dispatch after reopening the original work (attempts '
      + observation.attempts.before + '->' + observation.attempts.after + ', model requests '
      + observation.model_requests.before + '->' + observation.model_requests.after + ')', true);
  }
  return observation;
}

module.exports = { recordReplayObservation };

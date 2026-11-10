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
  // Only an observed comparison may claim zero new dispatches; an unavailable
  // before side stays explicitly unproven instead of being asserted as zero.
  if (observation.status === 'observed') {
    check('no new dispatch after reopening the original work (attempts '
      + observation.attempts.before + '->' + observation.attempts.after + ', model requests '
      + observation.model_requests.before + '->' + observation.model_requests.after + ')',
    observation.new_dispatches === 0);
  }
  return observation;
}

module.exports = { recordReplayObservation };

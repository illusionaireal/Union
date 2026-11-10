// Record a failed evidence read so the run leaves an attributable artifact behind.
// Read-only: it never issues a request and never invents a receipt or dispatch count.
function recordEvidenceFailure({ fs, path, output, name, workId, error }) {
  const reason = String((error && error.message) || error);
  const record = {
    protocol: 'acceptance.evidence-failure.v1',
    name,
    work_id: workId ?? null,
    status: 'failed',
    reason,
    dispatch_count: null,
    recorded_at: new Date().toISOString(),
  };
  fs.writeFileSync(path.join(output, name + '-failure.json'), JSON.stringify(record, null, 2));
  return record;
}

module.exports = { recordEvidenceFailure };

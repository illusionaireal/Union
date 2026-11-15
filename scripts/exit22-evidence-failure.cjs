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
    // Completed route outcomes are preserved when the loader recorded them: routes,
    // statuses and Core codes only, never response bodies or credentials.
    http: (error && error.http) || null,
    route: (error && error.route) || null,
    failed_status: (error && error.status) ?? null,
    code: (error && error.code) || null,
    dispatch_count: null,
    recorded_at: new Date().toISOString(),
  };
  fs.writeFileSync(path.join(output, name + '-failure.json'), JSON.stringify(record, null, 2));
  return record;
}

// Wrap a read-only evidence loader: on failure write the failure record, then rethrow.
async function readWithFailureRecord({ loader, fs, path, output, name, workId, ...rest }) {
  try {
    return await loader(rest);
  } catch (error) {
    recordEvidenceFailure({ fs, path, output, name, workId, error });
    throw error;
  }
}

module.exports = { recordEvidenceFailure, readWithFailureRecord };

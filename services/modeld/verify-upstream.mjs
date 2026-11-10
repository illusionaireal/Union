import { execFileSync } from 'node:child_process';

/** Keep the complete recorded patch comparison, including blob ids and hunks. */
export function assertRecordedUpstreamPatch(vendor, expected) {
  const actual = execFileSync('git', ['diff', '--no-ext-diff', '--abbrev=7'], {
    cwd: vendor, encoding: 'utf8', windowsHide: true,
  }).replaceAll('\r\n', '\n').trim();
  if (actual !== expected.replaceAll('\r\n', '\n').trim())
    throw new Error('Unrecorded upstream changes');
}

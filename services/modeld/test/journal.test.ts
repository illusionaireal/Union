import { afterEach, expect, test } from 'bun:test';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { Journal, type InferenceInput } from '../src/journal';

const directories: string[] = [], journals: Journal[] = [];
afterEach(() => { for (const j of journals.splice(0)) j.close(); for (const d of directories.splice(0)) rmSync(d, { recursive: true, force: true }); });
function setup() {
  const directory = mkdtempSync(join(tmpdir(), 'union-modeld-journal-'));
  directories.push(directory);
  const j = new Journal(directory); journals.push(j);
  j.createGrant({ id: 'grant-a', au_id: 'au-a', account_ref: 'account-a', model_ids: ['model-a'] });
  const input: InferenceInput = { id: 'run-a', run_id: 'run-a', au_id: 'au-a', connection_id: 'connection-a',
    connection_revision: 1, grant_ref: 'grant-a', grant_revision: 1, model_id: 'model-a',
    messages: [{ role: 'user', content: 'hello' }], tools: [], generation: { maxOutputTokens: 20 },
    deadlines: { first_event_ms: 180000, idle_ms: 120000, task_ms: null } };
  return { j, input, directory };
}
test('request replay returns the original state and never requeues a sent attempt', () => {
  const { j, input } = setup();
  expect(j.submit(input).created).toBe(true);
  j.begin(input.id, input.au_id);
  expect(j.submit({ ...input }).created).toBe(false);
  expect(j.begin(input.id, input.au_id)).toBeNull();
  expect(j.queued()).toHaveLength(0);
  expect(() => j.submit({ ...input, messages: [{ role: 'user', content: 'different' }] })).toThrow('request_id_conflict');
});
test('grants bind model and AU and cannot be re-created to erase revocation', () => {
  const { j, input } = setup();
  expect(() => j.submit({ ...input, au_id: 'au-b' })).toThrow('grant_unavailable');
  expect(() => j.submit({ ...input, model_id: 'model-b' })).toThrow('model_not_granted');
  j.submit(input);
  j.revoke('grant-a', 1);
  expect(j.get('run-a','au-a').state).toBe('failed');
  expect(() => j.createGrant({ id: 'grant-a', au_id: 'au-a', account_ref: 'account-a', model_ids: ['model-a'] })).toThrow('grant_id_conflict');
  expect(() => j.get('run-a','au-b')).toThrow('request_not_found');
  expect(() => j.events('run-a','au-b',0)).toThrow('request_not_found');
});
test('restart preserves partial events and fences an interrupted result without replay', () => {
  const { j, input, directory } = setup();
  j.submit(input); j.begin(input.id,input.au_id);
  j.event(input.id,'text_delta',{ text: 'partial' });
  j.close(); journals.splice(journals.indexOf(j),1);
  const reopened = new Journal(directory); journals.push(reopened);
  expect(reopened.get(input.id,input.au_id).state).toBe('interrupted');
  expect(reopened.queued()).toHaveLength(0);
  const all = reopened.events(input.id,input.au_id,0);
  expect(all.map(e => e.seq)).toEqual([1,2,3,4]);
  expect(all[2].payload.text).toBe('partial');
  expect(reopened.events(input.id,input.au_id,2)).toEqual(all.slice(2));
  reopened.finish(input.id,'completed',{ text: 'late' });
  expect(reopened.get(input.id,input.au_id).state).toBe('interrupted');
});
test('cancel is an intent; a late completion cannot become executable', () => {
  const { j, input } = setup();
  j.submit(input); j.begin(input.id,input.au_id);
  j.cancel(input.id,input.au_id);
  expect(() => j.event(input.id,'tool_call_complete',{ name: 'pay' })).toThrow('attempt_no_longer_current');
  j.finish(input.id,'completed',{ text: 'late' });
  expect(j.get(input.id,input.au_id).state).toBe('interrupted');
  expect(j.events(input.id,input.au_id,0).find(e => e.type === 'cancel_requested')?.payload.remote_cancellation_confirmed).toBe(false);
});

import { afterEach, expect, test } from 'bun:test';
import { Database } from 'bun:sqlite';
import { randomUUID } from 'node:crypto';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { basename, dirname, join, resolve } from 'node:path';
import { Journal } from '../src/journal';
import { validateAPIRegistration } from '../src/api-accounts';

const directories: string[] = [], journals: Journal[] = [];
afterEach(() => {
  for (const j of journals.splice(0)) j.close();
  for (const directory of directories.splice(0)) {
    expect(dirname(resolve(directory))).toBe(resolve(tmpdir()));
    expect(basename(directory).startsWith('union-responses-')).toBe(true);
    rmSync(directory, { recursive: true, force: true });
  }
});
function setup() {
  const directory = mkdtempSync(join(tmpdir(), 'union-responses-'));
  directories.push(directory);
  const journal = new Journal(directory); journals.push(journal);
  const input = { id: randomUUID(), au_id: randomUUID(), principal_id: randomUUID(), name: 'Responses fixture',
    base_url: 'http://127.0.0.1:32123/v1', api_key: 'responses-fixture-credential-92861', model_id: 'controlled-model' };
  return { directory, journal, input };
}
const version = (j: Journal) => (j.db.query('PRAGMA user_version').get() as any).user_version;

test('explicit Responses registration preserves old receipts and binds protocol/settings durably', () => {
  const { journal: j, input, directory } = setup();
  const old = j.registerAPI(validateAPIRegistration(input));
  const before = j.db.query('SELECT * FROM api_connections WHERE id=?').get(input.id) as any;
  expect(version(j)).toBe(0);
  const selected = { ...input, id: randomUUID(), wire_api: 'responses', reasoning_effort: 'max' };
  const receipt = j.registerAPI(validateAPIRegistration(selected));
  expect(receipt).toMatchObject({ profile: 'openai_responses', wire_api: 'responses', reasoning_effort: 'max' });
  expect(version(j)).toBe(1);
  expect(j.registerAPI(validateAPIRegistration(input))).toEqual(old);
  expect(j.db.query('SELECT digest FROM api_connections WHERE id=?').get(input.id)).toEqual({ digest: before.digest });
  expect(() => j.registerAPI(validateAPIRegistration({ ...selected, reasoning_effort: 'low' }))).toThrow('api_connection_id_conflict');
  expect(() => j.registerAPI(validateAPIRegistration({ ...selected, wire_api: 'chat_completions', reasoning_effort: undefined }))).toThrow();
  const account = j.apiAccount(j.grant(receipt.grant_ref).account_ref)!;
  expect(account).toMatchObject({ wire_api: 'responses', reasoning_effort: 'max' });
  j.close(); journals.splice(journals.indexOf(j), 1);
  const reopened = new Journal(directory); journals.push(reopened);
  expect(reopened.apiAccount(account.account_ref)).toEqual(account);
  expect(reopened.apiConnection(input.id, input.au_id, input.principal_id)).toEqual(old);
  expect(reopened.registerAPI(validateAPIRegistration(selected))).toEqual(receipt);
  reopened.revoke(receipt.grant_ref, 1);
  expect(reopened.registerAPI(validateAPIRegistration(selected))).toEqual(receipt);
  expect(reopened.grant(receipt.grant_ref).revision).toBe(2);
});

test('failed protocol registration rolls back schema, account and grant together', () => {
  const { journal: j, input } = setup();
  j.db.exec("CREATE TRIGGER deny_fixture BEFORE INSERT ON grant_audit BEGIN SELECT RAISE(ABORT,'fixture'); END");
  const selected = validateAPIRegistration({ ...input, wire_api: 'responses', reasoning_effort: 'max' });
  expect(() => j.registerAPI(selected)).toThrow('fixture');
  expect(version(j)).toBe(0);
  expect((j.db.query('PRAGMA table_info(api_connections)').all() as any[]).some(x => x.name === 'options')).toBe(false);
  expect(j.db.query('SELECT COUNT(*) AS n FROM grants').get()).toEqual({ n: 0 });
  expect(j.db.query('SELECT COUNT(*) AS n FROM api_connections').get()).toEqual({ n: 0 });
});

test('unsupported protocol or settings are rejected without changing the private schema', () => {
  const { journal: j, input } = setup();
  for (const settings of [{ wire_api: 'auto' }, { reasoning_effort: 'max' },
    { wire_api: 'responses', reasoning_effort: 'unlimited' }, { wire_api: 'chat_completions', reasoning_effort: 'max' }])
    expect(() => j.registerAPI(validateAPIRegistration({ ...input, ...settings }))).toThrow();
  expect(version(j)).toBe(0);
});

test('unknown private schemas are rejected before interrupted request recovery writes', () => {
  const { journal: j, directory } = setup();
  j.db.exec('PRAGMA user_version=8');
  j.close(); journals.splice(journals.indexOf(j), 1);
  let opened: Journal | undefined, failure: any;
  try { opened = new Journal(directory); } catch (error) { failure = error; }
  opened?.close();
  expect(failure?.message).toBe('unsupported_modeld_schema');
  const db = new Database(join(directory, 'modeld.sqlite3'), { readonly: true });
  expect(db.query('PRAGMA user_version').get()).toEqual({ user_version: 8 }); db.close();
});

test('Responses runs the pinned HTTP stream with original native tools, usage and safe errors', async () => {
  const child = Bun.spawn([process.execPath, join(import.meta.dir, 'fixtures/responses-probe.ts')], { stdout: 'pipe', stderr: 'pipe' });
  const [stdout, stderr, code] = await Promise.all([new Response(child.stdout).text(), new Response(child.stderr).text(), child.exited]);
  if (code) throw new Error(stdout + stderr);
  const result = JSON.parse(stdout.trim().split('\n').at(-1)!);
  expect(result).toMatchObject({ real_model_calls: 0, roundtrip: true, native_replay: true, separate_usage: true,
    exact_settings: true, safe_errors: true, no_retry: true });
}, 30000);

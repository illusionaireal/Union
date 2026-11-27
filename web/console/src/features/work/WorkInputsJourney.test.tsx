import {act, fireEvent, screen, waitFor} from '@testing-library/react';
import {afterEach, beforeEach, expect, it, vi} from 'vitest';
import {createHash, webcrypto} from 'node:crypto';
import {fixture, mount} from '../models/test-fixtures';
import {api, ApiError} from '../../api/client';
import type {CoreWork} from '../../api/types';

let state: ReturnType<typeof fixture>;
let read: CoreWork;
let requests: Record<string, unknown>[];
const receipts = new Map<string, unknown>();
const content = '请保留原来源\n<script>window.inputExecuted=true</script>';
const sha = (body: string) => createHash('sha256').update(body).digest('hex');
const metadata = (body = content, seq = 1, status = 'received') => ({
  id: `input-${String(seq).padStart(32, '0')}`, seq, sha256: sha(body), bytes: Buffer.byteLength(body),
  source_kind: 'requirement', actor_principal_id: state.session.principal_id,
  received_at: '2026-11-26T00:00:00Z', reason: '补充来源',
  source_scope: {member_id: 'member-one', binding_id: 'binding-one', binding_version: 1,
    definition_id: 'definition-one', definition_version: 1, mandate_id: 'mandate-one', mandate_version: 1,
    charter_version: 1, policy_version: 1},
  status, attachments: [],
});
beforeEach(() => {
  state = fixture(); requests = []; receipts.clear(); vi.stubGlobal('crypto', webcrypto);
  read = {protocol: 'core.work.v1', organization_id: 'core-au', version: 12,
    access: Object.assign({principal_id: state.session.principal_id!, can_start: false, can_manage_results: false}, {can_append_input: true, can_read_inputs: true}),
    capabilities: {work_registration: true, execution: 'unavailable', autonomous_business: false}, works: [{
      id: 'work-original', title: '原长工作', goal: '研究原资料', status: 'running', version: 1, max_calls: 2,
      materials_root: null, created_at: '', responsible: {member_id: 'member-one', name: '研究成员', binding_id: 'binding-one', duty: '研究'},
      definition: {id: 'definition-one', version: 1, connection_id: 'connection-one', model: 'controlled-model', tools: []},
      mandate: {id: 'mandate-one', version: 1, actions: [], active: true}, attempt_ids: [], result_ids: [],
      tool_calls: [], attempts: [], steps: [], budget: {max_calls: 2, reserved: 2, used: 0},
      materials: {reference: null, available: false, documents: 0}, results: [],
    }]};
  Object.assign(read.works[0], {input_seq: 0, input_cursor: 0, inputs: [], input_summary: {received: 0, attached: 0, observed: 0, consumed: 0, pending: 0}});
  vi.spyOn(api, 'coreWork').mockImplementation(async () => structuredClone(read));
  vi.spyOn(api, 'coreWorkCommand').mockImplementation(async request => {
    requests.push(request); const data = request.data as Record<string, string>;
    const input = {...metadata(data.content), id: data.input_id, reason: data.reason};
    Object.assign(read.works[0], {input_seq: 1, inputs: [input], input_summary: {received: 1, attached: 0, observed: 0, consumed: 0, pending: 1}});
    read.version++; state.core.au.version = read.version;
    const receipt = {id: String(request.id), kind: request.kind, organization_id: 'core-au', base_version: request.base_version,
      actor_principal_id: state.session.principal_id, status: 'succeeded', version: read.version,
      work_id: 'work-original', input, message: '输入已收存；尚未采用'};
    receipts.set(String(request.id), receipt); return {receipt};
  });
  vi.spyOn(api, 'coreWorkReceipt').mockImplementation(async (_, id) => {
    if (!receipts.has(id)) throw Object.assign(new Error('原回执尚未可读'), {status: 404});
    return {receipt: receipts.get(id)};
  });
});
afterEach(() => vi.unstubAllGlobals());
async function fill(body = content) {
  await screen.findByRole('heading', {name: '原长工作'});
  fireEvent.change(screen.getByLabelText('补充输入正文'), {target: {value: body}});
  fireEvent.change(screen.getByLabelText('补充依据'), {target: {value: '补充来源'}});
  return screen.getByRole('button', {name: '收存补充输入'});
}

it('appends to the original Work while model, budget and recovery are unavailable, with only frozen command fields', async () => {
  mount('/au/core-au/work/work-original'); fireEvent.click(await fill());
  await screen.findByText('输入已收存；尚未采用'); expect(requests).toHaveLength(1);
  expect(Object.keys(requests[0]).sort()).toEqual(['base_version', 'data', 'id', 'kind', 'organization_id']);
  expect(requests[0].kind).toBe('append_work_input');
  expect(requests[0].data).toEqual({work_id: 'work-original', input_id: expect.stringMatching(/^input-[a-f0-9]{32}$/), content, reason: '补充来源'});
  const cache = JSON.stringify(sessionStorage); expect(cache).toContain(String(requests[0].id)); expect(cache).toContain(sha(content));
  expect(cache).not.toContain(content); expect(cache).not.toContain('补充来源');
  expect(screen.getByText(/仍待采用 1 项/)).toBeVisible();
});

it('keeps lost response and 404 as original queries across service restart, without another POST', async () => {
  const send = vi.mocked(api.coreWorkCommand).getMockImplementation()!;
  vi.mocked(api.coreWorkCommand).mockImplementation(async request => {await send(request); throw new Error('丢失响应');});
  const mounted = mount('/au/core-au/work/work-original'); fireEvent.click(await fill());
  await screen.findByRole('button', {name: '查询输入原请求'}); const original = String(requests[0].id);
  mounted.view.unmount(); state.session.service_instance = 'new-service'; state.core.access.service_instance = 'new-service';
  mount('/au/core-au/work/work-original');
  expect((await screen.findByLabelText('补充输入正文'))).toHaveValue('');
  const receipt = receipts.get(original); receipts.delete(original);
  fireEvent.click(screen.getByRole('button', {name: '查询输入原请求'})); await screen.findByText('原回执尚未可读');
  expect(screen.getByRole('button', {name: '收存补充输入'})).toBeDisabled();
  receipts.set(original, receipt); fireEvent.click(screen.getByRole('button', {name: '查询输入原请求'}));
  await screen.findByText('输入已收存；尚未采用'); expect(requests).toHaveLength(1);
  expect(api.coreWorkReceipt).toHaveBeenCalledWith('core-au', original);
});

it('retains draft on known refusal and requires explicit new intent, never replaying old input', async () => {
  const send = vi.mocked(api.coreWorkCommand).getMockImplementation()!;
  vi.mocked(api.coreWorkCommand).mockImplementation(async request => {requests.push(request); const receipt = {
    id: String(request.id), kind: request.kind, organization_id: 'core-au', base_version: request.base_version,
    actor_principal_id: state.session.principal_id, version: read.version, status: 'rejected', message: '工作已结束，未重开'};
    receipts.set(String(request.id), receipt); return {receipt};});
  mount('/au/core-au/work/work-original'); fireEvent.click(await fill()); await screen.findByText('工作已结束，未重开');
  expect(screen.getByLabelText('补充输入正文')).toHaveValue(content);
  fireEvent.click(screen.getByRole('button', {name: '继续补充输入'}));
  vi.mocked(api.coreWorkCommand).mockImplementation(send); fireEvent.click(screen.getByRole('button', {name: '收存补充输入'}));
  await screen.findByText('输入已收存；尚未采用'); expect(requests).toHaveLength(2); expect(requests[0].id).not.toBe(requests[1].id);
});

it('keeps historic input readable after this Work closes without offering a new submission', async () => {
  const input = metadata();
  Object.assign(read.works[0], {status: 'delivered', inputs: [input]});
  vi.spyOn(api, 'coreWorkInput').mockResolvedValue({protocol: 'core.work-input.v1', organization_id: 'core-au',
    work_id: 'work-original', input, content} as Awaited<ReturnType<typeof api.coreWorkInput>>);
  mount('/au/core-au/work/work-original');
  expect(await screen.findByLabelText('补充输入正文')).toBeDisabled();
  expect(screen.getByRole('button', {name: '收存补充输入'})).toBeDisabled();
  fireEvent.click(screen.getByRole('button', {name: '阅读输入正文'}));
  expect(await screen.findByLabelText('已收存输入正文')).toHaveTextContent(/请保留原来源/);
  expect(requests).toHaveLength(0);
});

it('keeps legal Work reading and the original ID after a direct input-only authority refusal', async () => {
  vi.mocked(api.coreWorkCommand).mockImplementation(async request => {
    requests.push(request);
    Object.assign(read.access, {can_append_input: false, can_read_inputs: false});
    throw Object.assign(new Error('当前不能提交补充输入'), {status: 403});
  });
  mount('/au/core-au/work/work-original'); fireEvent.click(await fill());
  await screen.findByRole('button', {name: '查询输入原请求'});
  await waitFor(() => expect(screen.getByLabelText('补充输入正文')).toHaveValue(''));
  expect(screen.getByRole('heading', {name: '原长工作'})).toBeVisible();
  expect(screen.getByRole('button', {name: '收存补充输入'})).toBeDisabled();
  expect(requests).toHaveLength(1);
});

it.each(['oversize', 'NUL', 'surrogate'])('refuses %s input before POST without truncating the draft', async kind => {
  const body = kind === 'oversize' ? '中'.repeat(21846) : kind === 'NUL' ? 'a\0b' : 'a\ud800b';
  mount('/au/core-au/work/work-original'); const button = await fill(body); fireEvent.click(button);
  await screen.findByText(/输入须为有效 UTF-8 文本/); expect(requests).toHaveLength(0);
  expect(screen.getByLabelText('补充输入正文')).toHaveValue(body);
});

it('clears private draft when append permission changes but keeps legal Work reading', async () => {
  mount('/au/core-au/work/work-original'); await fill(); Object.assign(read.access, {can_append_input: false});
  fireEvent.click(screen.getByRole('button', {name: '刷新工作资料依据'}));
  await waitFor(() => expect(screen.getByLabelText('补充输入正文')).toHaveValue(''));
  expect(screen.getByRole('heading', {name: '原长工作'})).toBeVisible(); expect(screen.getByRole('button', {name: '收存补充输入'})).toBeDisabled();
});

it('automatically clears opened private input and draft when the visible Work loses permissions', async () => {
  const input = metadata();
  Object.assign(read.works[0], {inputs: [input]});
  vi.spyOn(api, 'coreWorkInput').mockResolvedValue({protocol: 'core.work-input.v1', organization_id: 'core-au',
    work_id: 'work-original', input, content} as Awaited<ReturnType<typeof api.coreWorkInput>>);
  mount('/au/core-au/work/work-original'); await fill('私有草稿');
  fireEvent.click(screen.getByRole('button', {name: '阅读输入正文'}));
  await screen.findByLabelText('已收存输入正文');
  Object.assign(read.access, {can_append_input: false, can_read_inputs: false});
  await waitFor(() => expect(screen.getByLabelText('补充输入正文')).toHaveValue(''), {timeout: 6000});
  expect(screen.queryByLabelText('已收存输入正文')).toBeNull();
  expect(screen.getByRole('heading', {name: '原长工作'})).toBeVisible();
}, 8000);

it('preserves a scoped draft after a transient Work read error', async () => {
  mount('/au/core-au/work/work-original'); await fill('需要保留的授权草稿');
  vi.mocked(api.coreWork).mockRejectedValueOnce(Object.assign(new Error('临时读取失败'), {status: 503}));
  fireEvent.click(screen.getByRole('button', {name: '刷新工作资料依据'}));
  await screen.findByText(/临时读取失败/);
  expect(screen.getByLabelText('补充输入正文')).toHaveValue('需要保留的授权草稿');
  expect(requests).toHaveLength(0);
});

it('records a delayed definite refusal after observed intake loss clears the draft', async () => {
  let refuse!: () => void;
  vi.mocked(api.coreWorkCommand).mockImplementation(request => new Promise((_, reject) => {
    requests.push(request);
    refuse = () => reject(Object.assign(new Error('当前不能收存'), {status: 403}));
  }));
  mount('/au/core-au/work/work-original'); fireEvent.click(await fill());
  await waitFor(() => expect(requests).toHaveLength(1));
  Object.assign(read.access, {can_append_input: false, can_read_inputs: false});
  fireEvent.click(screen.getByRole('button', {name: '刷新工作资料依据'}));
  await waitFor(() => expect(screen.getByLabelText('补充输入正文')).toHaveValue(''));
  refuse();
  await screen.findByText('原提交已明确被拒绝，没有收存新输入。');
  expect(requests).toHaveLength(1);
});

it('allows explicit new input after a direct auth refusal, preserving the original refused request history', async () => {
  const send = vi.mocked(api.coreWorkCommand).getMockImplementation()!;
  vi.mocked(api.coreWorkCommand).mockImplementation(async request => {requests.push(request); throw Object.assign(new Error('not permitted'), {status: 401});});
  const opened = mount('/au/core-au/work/work-original'); fireEvent.click(await fill());
  await screen.findByRole('alert'); const original = String(requests[0].id); opened.view.unmount();
  vi.mocked(api.coreWorkCommand).mockImplementation(send); mount('/au/core-au/work/work-original');
  fireEvent.click(await screen.findByRole('button', {name: '继续补充输入'}));
  fireEvent.click(await fill('重新登录后明确提出的要求')); await screen.findByText('输入已收存；尚未采用');
  expect(requests).toHaveLength(2); expect(requests[1].id).not.toBe(original); expect(JSON.stringify(sessionStorage)).toContain(original);
});

it('keeps a succeeded POST unresolved after later auth loss and reopens only its original query', async () => {
  const send = vi.mocked(api.coreWorkCommand).getMockImplementation()!;
  const getWork = vi.mocked(api.coreWork).getMockImplementation()!;
  vi.mocked(api.coreWorkCommand).mockImplementation(async request => {
    const response = await send(request); vi.mocked(api.coreWork).mockRejectedValue(Object.assign(new Error('read denied'), {status: 403})); return response;
  });
  const opened = mount('/au/core-au/work/work-original'); fireEvent.click(await fill());
  await screen.findByRole('alert'); const original = String(requests[0].id); opened.view.unmount();
  vi.mocked(api.coreWork).mockImplementation(getWork); mount('/au/core-au/work/work-original');
  fireEvent.click(await screen.findByRole('button', {name: '查询输入原请求'})); await screen.findByText('输入已收存；尚未采用');
  expect(requests).toHaveLength(1); expect(api.coreWorkReceipt).toHaveBeenCalledWith('core-au', original);
});

it('rejects a foreign input success receipt while keeping its original query unresolved', async () => {
  const send = vi.mocked(api.coreWorkCommand).getMockImplementation()!;
  vi.mocked(api.coreWorkCommand).mockImplementation(async request => {
    const response = await send(request) as {receipt: Record<string, unknown>};
    (response.receipt.input as Record<string, unknown>).sha256 = 'a'.repeat(64); return response as never;
  });
  mount('/au/core-au/work/work-original'); fireEvent.click(await fill());
  await screen.findByText('回执与原请求不匹配'); expect(screen.getByRole('button', {name: '收存补充输入'})).toBeDisabled();
  expect(screen.queryByRole('button', {name: '继续补充输入'})).toBeNull();
});

it('reads historical input with legal read access after intake has ended', async () => {
  const input = metadata(); Object.assign(read.works[0], {inputs: [input]});
  Object.assign(read.access, {can_append_input: false, can_read_inputs: true});
  const original = vi.mocked(fetch).getMockImplementation()!;
  vi.mocked(fetch).mockImplementation(async (url, init) => String(url).startsWith('/api/v1/work/inputs?') ?
    {ok: true, json: async () => ({protocol: 'core.work-input.v1', organization_id: 'core-au', work_id: 'work-original', input, content})} as Response : original(url, init));
  mount('/au/core-au/work/work-original');
  fireEvent.click(await screen.findByRole('button', {name: '阅读输入正文'}));
  expect((await screen.findByLabelText('已收存输入正文')).textContent).toBe(content);
  expect(screen.getByRole('button', {name: '收存补充输入'})).toBeDisabled(); expect(requests).toHaveLength(0);
});

it('does not request private input body for a non-governor with legal metadata reading', async () => {
  Object.assign(read.works[0], {inputs: [metadata()]}); Object.assign(read.access, {can_append_input: false, can_read_inputs: false});
  mount('/au/core-au/work/work-original'); const button = await screen.findByRole('button', {name: '阅读输入正文'});
  expect(button).toBeDisabled(); fireEvent.click(button); expect(screen.queryByLabelText('已收存输入正文')).toBeNull();
  expect(vi.mocked(fetch).mock.calls.filter(([url]) => String(url).startsWith('/api/v1/work/inputs?'))).toHaveLength(0);
});

it('retains a definite append format refusal across restart and corrects it only with an explicit new ID', async () => {
  const send = vi.mocked(api.coreWorkCommand).getMockImplementation()!;
  vi.mocked(api.coreWorkCommand).mockImplementation(async request => {requests.push(request); throw new ApiError('确定格式拒绝', 400, 'invalid_request');});
  const opened = mount('/au/core-au/work/work-original'); fireEvent.click(await fill()); await screen.findByText('确定格式拒绝');
  expect(screen.getByLabelText('补充输入正文')).toHaveValue(content);
  expect(screen.getByRole('button', {name: '继续补充输入'})).toBeEnabled();
  const original = String(requests[0].id); opened.view.unmount();
  mount('/au/core-au/work/work-original'); fireEvent.click(await screen.findByRole('button', {name: '继续补充输入'}));
  vi.mocked(api.coreWorkCommand).mockImplementation(send); fireEvent.click(await fill('明确更正后的新输入'));
  await screen.findByText('输入已收存；尚未采用'); expect(requests).toHaveLength(2); expect(requests[1].id).not.toBe(original);
  expect(JSON.stringify(sessionStorage)).toContain(original);
});

it.each([400, 409])('keeps an append HTTP %s without an exact format-refusal code unresolved', async status => {
  vi.mocked(api.coreWorkCommand).mockImplementation(async request => {requests.push(request); throw new ApiError('未确认的拒绝', status, 'other_error');});
  mount('/au/core-au/work/work-original'); fireEvent.click(await fill()); await screen.findByText('未确认的拒绝');
  expect(screen.queryByRole('button', {name: '继续补充输入'})).toBeNull(); expect(screen.getByRole('button', {name: '查询输入原请求'})).toBeEnabled();
});

it('keeps a successful append unresolved when only later Work reading returns 400 invalid_request', async () => {
  const send = vi.mocked(api.coreWorkCommand).getMockImplementation()!;
  vi.mocked(api.coreWorkCommand).mockImplementation(async request => {
    const response = await send(request); vi.mocked(api.coreWork).mockRejectedValue(new ApiError('后续读取格式错误', 400, 'invalid_request')); return response;
  });
  mount('/au/core-au/work/work-original'); fireEvent.click(await fill()); await screen.findByText('后续读取格式错误');
  expect(screen.queryByRole('button', {name: '继续补充输入'})).toBeNull(); expect(screen.getByRole('button', {name: '查询输入原请求'})).toBeEnabled();
});

it('accepts explicit schema 6 while refusing unsupported schema 7', async () => {
  Object.assign(state.core.au, {schema_version: 6}); const opened = mount('/au/core-au/work/work-original');
  await screen.findByLabelText('补充输入正文'); opened.view.unmount(); Object.assign(state.core.au, {schema_version: 7});
  mount('/au/core-au/work/work-original'); await screen.findByRole('alert');
  expect(screen.queryByLabelText('补充输入正文')).toBeNull();
});

it('distinguishes all input states and provenance without treating consumption as requirement fulfillment', async () => {
  Object.assign(read.works[0], {inputs: ['received', 'attached', 'observed', 'consumed'].map((s, i) => metadata(content, i + 1, s)),
    input_seq: 4, input_cursor: 0, input_summary: {received: 1, attached: 1, observed: 1, consumed: 1, pending: 3}});
  mount('/au/core-au/work/work-original');
  for (const label of ['已收存', '已附入原请求', '模型已观察', '已正式采用']) expect(await screen.findByText(label, {exact: true})).toBeVisible();
  expect(screen.getByText(/正式采用表示进入执行上下文，不表示要求已经实现/)).toBeVisible();
  expect(screen.getByText(/仍待采用 3 项/)).toBeVisible(); expect(screen.getAllByText(/member-one/).length).toBeGreaterThan(0);
});

it.each(['identity', 'work', 'digest'])('rejects %s mismatch in private input body before showing text', async field => {
  const input = metadata(); Object.assign(read.works[0], {inputs: [input]});
  const reply = {protocol: 'core.work-input.v1', organization_id: 'core-au', work_id: 'work-original', input, content};
  const original = vi.mocked(fetch).getMockImplementation()!;
  vi.mocked(fetch).mockImplementation(async (url, init) => {
    if (String(url).startsWith('/api/v1/work/inputs?')) {
      if (field === 'identity') reply.organization_id = 'foreign-au';
      if (field === 'work') reply.work_id = 'foreign-work';
      if (field === 'digest') reply.content = 'corrupted body';
      return {ok: true, json: async () => reply} as Response;
    }
    return original(url, init);
  });
  mount('/au/core-au/work/work-original'); fireEvent.click(await screen.findByRole('button', {name: '阅读输入正文'}));
  await screen.findByText(/输入身份、来源或正文校验失败/); expect(screen.queryByLabelText('已收存输入正文')).toBeNull();
});

it.each(['can_append_input', 'can_read_inputs'])('checks the late input body against independent read authority after %s loss', async permission => {
  const input = metadata(); Object.assign(read.works[0], {inputs: [input]});
  let finish!: (response: Response) => void; let delayed = false;
  const original = vi.mocked(fetch).getMockImplementation()!;
  vi.mocked(fetch).mockImplementation(async (url, init) => {
    if (String(url).startsWith('/api/v1/work/inputs?')) {
      const reply = {ok: true, json: async () => ({protocol: 'core.work-input.v1', organization_id: 'core-au', work_id: 'work-original', input, content})} as Response;
      return delayed ? new Promise<Response>(resolve => {finish = resolve;}) : reply;
    }
    return original(url, init);
  });
  mount('/au/core-au/work/work-original'); fireEvent.click(await screen.findByRole('button', {name: '阅读输入正文'}));
  const body = await screen.findByLabelText('已收存输入正文'); expect(body.textContent).toBe(content); expect(body.querySelector('script')).toBeNull();
  fireEvent.click(screen.getByRole('button', {name: '收起输入正文'})); delayed = true;
  fireEvent.click(screen.getByRole('button', {name: '阅读输入正文'})); await waitFor(() => expect(finish).toBeDefined());
  Object.assign(read.access, {[permission]: false}); fireEvent.click(screen.getByRole('button', {name: '刷新工作资料依据'}));
  if (permission === 'can_read_inputs') {
    const readButton = await screen.findByRole('button', {name: '阅读输入正文'});
    expect(readButton).toBeDisabled();
  } else {
    await waitFor(() => expect(screen.getByLabelText('补充输入正文')).toBeDisabled());
  }
  await act(async () => finish({ok: true, json: async () => ({protocol: 'core.work-input.v1', organization_id: 'core-au', work_id: 'work-original', input, content})} as Response));
  if (permission === 'can_read_inputs') expect(screen.queryByLabelText('已收存输入正文')).toBeNull();
  else expect((await screen.findByLabelText('已收存输入正文')).textContent).toBe(content);
  expect(JSON.stringify(sessionStorage)).not.toContain(content);
});

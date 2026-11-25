import { act, fireEvent, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { fixture, mount } from './test-fixtures';
import { api } from '../../api/client';
import { webcrypto, createHash } from 'node:crypto';

let state: ReturnType<typeof fixture>;
let items: import('../../api/types').BusinessMaterial[];
const receipts = new Map<string, unknown>();

beforeEach(() => {
  state = fixture(); items = []; receipts.clear();
  vi.stubGlobal('crypto', webcrypto);
  vi.mocked(api.coreMaterials).mockImplementation(async () => ({ protocol: 'core.materials.v1',
    organization_id: 'core-au', version: state.read.version,
    access: { principal_id: state.read.access.principal_id, can_manage: true },
    limits: { bytes_per_material: 65536, materials: 16, total_bytes: 1048576 }, materials: structuredClone(items) }));
  vi.spyOn(api, 'coreWork').mockImplementation(async () => ({protocol: 'core.work.v1', organization_id: 'core-au',
    version: state.read.version, access: { principal_id: state.read.access.principal_id, can_start: true, can_manage_results: true },
    works: [], capabilities: { work_registration: true, execution: 'not_started', autonomous_business: false } }));
  vi.spyOn(api, 'coreWorkCommand').mockImplementation(async request => {
    const data = request.data as Record<string, string>;
    state.read.version++;
    const item = {id: data.material_id, name: data.name, source: data.source as 'paste', scope: 'au_read_only' as const,
      version: 1, sha256: createHash('sha256').update(data.content).digest('hex'), bytes: Buffer.byteLength(data.content),
      read_allowed: true, created_at: '', reason: data.reason};
    items.push(item);
    const receipt = {id: String(request.id), kind: request.kind, organization_id: request.organization_id,
      base_version: request.base_version, version: state.read.version, actor_principal_id: state.read.access.principal_id,
      status: 'succeeded', message: '资料已导入并授权本组织只读；未调用模型', material: item};
    receipts.set(String(request.id), receipt);
    return {receipt};
  });
  vi.spyOn(api, 'coreWorkReceipt').mockImplementation(async (_, id) => ({receipt: receipts.get(id)}));
});
afterEach(() => { vi.unstubAllGlobals(); });

it('offers business-material preparation in the same AU resource journey', async () => {
  mount('/au/core-au/resources');
  expect(await screen.findByRole('region', { name: '业务资料' })).toBeVisible();
  expect(await screen.findByRole('button', { name: '选择或粘贴业务资料' })).toBeEnabled();
});

async function preview() {
  fireEvent.click(await screen.findByRole('button', { name: '选择或粘贴业务资料' }));
  fireEvent.change(screen.getByLabelText('资料名称'), {target: {value: '业务测试.md'}});
  fireEvent.change(screen.getByLabelText('业务资料正文'), {target: {value: '私有业务正文：三个模块'}});
  fireEvent.click(screen.getByRole('button', {name: '预览资料与授权'}));
  return screen.findByRole('button', {name: '确认导入并授权只读'});
}

it('previews scope and digest then imports one text with zero model dispatch and no stored draft', async () => {
  mount('/au/core-au/resources');
  const confirm = await preview();
  expect(api.coreWorkCommand).not.toHaveBeenCalled();
  fireEvent.click(confirm);
  await screen.findByText('资料已导入并授权本组织只读；未调用模型');
  expect(api.coreWorkCommand).toHaveBeenCalledTimes(1);
  expect(state.commands).toEqual([]);
  expect(JSON.stringify(sessionStorage)).not.toMatch(/私有业务正文|业务测试/);
  fireEvent.click(screen.getByRole('button', {name: '返回资料列表'}));
  await screen.findByText('业务测试.md');
});

it('reopens an unknown import by its original ID without importing the text again', async () => {
  const save = vi.mocked(api.coreWorkCommand).getMockImplementation()!;
  vi.mocked(api.coreWorkCommand).mockImplementation(async request => {await save(request); throw new Error('受控丢失响应');});
  const current = mount('/au/core-au/resources');
  fireEvent.click(await preview());
  await screen.findByText('受控丢失响应');
  current.view.unmount();
  mount('/au/core-au/resources');
  fireEvent.click(await screen.findByRole('button', {name: '选择或粘贴业务资料'}));
  fireEvent.click(await screen.findByRole('button', {name: '查询导入原请求'}));
  await screen.findByText('资料已导入并授权本组织只读；未调用模型');
  expect(api.coreWorkCommand).toHaveBeenCalledTimes(1);
});

it('keeps an unknown material reference across a process restart for explicit lookup only', async () => {
  const save = vi.mocked(api.coreWorkCommand).getMockImplementation()!;
  vi.mocked(api.coreWorkCommand).mockImplementation(async request => {await save(request); throw new Error('受控丢失响应');});
  const current = mount('/au/core-au/resources');
  fireEvent.click(await preview()); await screen.findByText('受控丢失响应');
  const id = String(vi.mocked(api.coreWorkCommand).mock.calls[0][0].id);
  current.view.unmount(); state.session.service_instance = 'restarted-service';
  state.core.access.service_instance = state.session.service_instance;
  state.read.access.service_instance = state.session.service_instance;
  mount('/au/core-au/resources');
  fireEvent.click(await screen.findByRole('button', {name: '选择或粘贴业务资料'}));
  fireEvent.click(await screen.findByRole('button', {name: '查询导入原请求'}));
  await screen.findByText('资料已导入并授权本组织只读；未调用模型');
  expect(api.coreWorkReceipt).toHaveBeenCalledWith('core-au', id);
  expect(api.coreWorkCommand).toHaveBeenCalledTimes(1);
});

it('refuses POST if it cannot preserve the original request', async () => {
  mount('/au/core-au/resources');
  const confirm = await preview();
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {throw new Error('storage refused');});
  fireEvent.click(confirm);
  await screen.findByText('浏览器无法保留原请求，尚未提交');
  expect(api.coreWorkCommand).not.toHaveBeenCalled();
});

it('retains the selected text when the organization version changes before confirmation', async () => {
  mount('/au/core-au/resources');
  const confirm = await preview();
  state.read.version++;
  fireEvent.click(confirm);
  await screen.findByText('配置或版本已变化，请刷新核对后提交');
  expect(screen.getByLabelText('业务资料正文')).toHaveValue('私有业务正文：三个模块');
  expect(api.coreWorkCommand).not.toHaveBeenCalled();
});

it('provides the same-AU work material preparation entry', async () => {
  mount('/au/core-au/work');
  expect(await screen.findByRole('region', {name: '工作资料准备'})).toBeVisible();
});

it('does not overwrite newer pasted text with a late file decode', async () => {
  mount('/au/core-au/resources');
  fireEvent.click(await screen.findByRole('button', {name: '选择或粘贴业务资料'}));
  let resolve!: (value: ArrayBuffer) => void;
  const file = {name: 'older.md', size: 5, arrayBuffer: () => new Promise<ArrayBuffer>(r => {resolve = r;})};
  fireEvent.change(screen.getByLabelText('选择 UTF-8 文本文件'), {target: {files: [file]}});
  fireEvent.change(screen.getByLabelText('业务资料正文'), {target: {value: '用户后来输入的资料'}});
  await act(async () => resolve(new TextEncoder().encode('old').buffer));
  expect(screen.getByLabelText('业务资料正文')).toHaveValue('用户后来输入的资料');
});

it.each(['denied', 'principal', 'service'] as const)('clears the unsubmitted body when preview loses %s authorization', async cause => {
  mount('/au/core-au/resources');
  fireEvent.click(await screen.findByRole('button', {name: '选择或粘贴业务资料'}));
  fireEvent.change(screen.getByLabelText('业务资料正文'), {target: {value: '不得向另一主体保留的正文'}});
  if (cause === 'denied') vi.mocked(api.coreMaterials).mockRejectedValueOnce(Object.assign(new Error('revoked'), {status: 403}));
  if (cause === 'principal') {
    const read = vi.mocked(api.coreMaterials).getMockImplementation()!;
    vi.mocked(api.coreMaterials).mockImplementationOnce(async (...args) => ({...await read(...args),
      access: {principal_id: 'another-principal', can_manage: true}}));
  }
  if (cause === 'service') {
    const session = await api.session();
    vi.mocked(api.session).mockResolvedValue({...session, service_instance: 'another-service'});
  }
  fireEvent.click(screen.getByRole('button', {name: '预览资料与授权'}));
  await waitFor(() => expect(screen.queryByDisplayValue('不得向另一主体保留的正文')).not.toBeInTheDocument());
  expect(api.coreWorkCommand).not.toHaveBeenCalled();
});

it('clears newer draft edits after a delayed read denial in the same scope', async () => {
  mount('/au/core-au/resources');
  fireEvent.click(await screen.findByRole('button', {name: '选择或粘贴业务资料'}));
  fireEvent.change(screen.getByLabelText('业务资料正文'), {target: {value: '原正文'}});
  let reject!: (error: unknown) => void;
  vi.mocked(api.coreMaterials).mockImplementationOnce(() => new Promise((_, r) => {reject = r;}));
  fireEvent.click(screen.getByRole('button', {name: '预览资料与授权'}));
  await waitFor(() => expect(reject).toBeTypeOf('function'));
  fireEvent.change(screen.getByLabelText('业务资料正文'), {target: {value: '新正文也应清除'}});
  await act(async () => reject(Object.assign(new Error('late denial'), {status: 403})));
  await waitFor(() => expect(screen.queryByDisplayValue('新正文也应清除')).not.toBeInTheDocument());
  expect(api.coreWorkCommand).not.toHaveBeenCalled();
});

it('refuses an explicit missing Work instead of showing another work context', async () => {
  mount('/au/core-au/work/missing-work');
  expect(await screen.findByText('指定工作不存在或不属于当前组织，未读取其他工作内容。')).toBeVisible();
});

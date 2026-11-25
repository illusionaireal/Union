import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { errorText } from '../../api/client';
import type { BusinessMaterial, CoreMaterials } from '../../api/types';
import { useWorkspace } from '../../app/workspace';
import { organizationPath } from '../../app/organization-routes';
import { Dialog } from '../../components/Dialog';
import { accessLost, useWorkCommand, type WorkScope } from '../work/useWorkCommand';
import { checkMaterials, useMaterials } from './useMaterials';
import { api } from '../../api/client';
import './materials.css';

type Draft = { name: string; content: string; source: 'file' | 'paste'; reason: string };
type Preview = Draft & { id: string; sha256: string; bytes: number; version: number };
const digest = async (content: string) => Array.from(new Uint8Array(await crypto.subtle.digest(
  'SHA-256', new TextEncoder().encode(content)))).map(x => x.toString(16).padStart(2, '0')).join('');

function MaterialImport({ scope, read, onClose, onAccessLost }: {
  scope: WorkScope; read: CoreMaterials; onClose: () => void; onAccessLost: () => void;
}) {
  const [draft, setDraft] = useState<Draft>({ name: '业务资料.md', content: '', source: 'paste', reason: '用于本组织的资料工作，只读所选正文' });
  const [preview, setPreview] = useState<Preview>();
  const [note, setNote] = useState('');
  const [preparing, setPreparing] = useState(false);
  const generation = useRef(0);
  const alive = useRef(true);
  useEffect(() => { alive.current = true; return () => { alive.current = false; generation.current++; }; }, []);
  const command = useWorkCommand(scope, onAccessLost, { kind: 'import_material', sha256: preview?.sha256 });
  const edit = (patch: Partial<Draft>) => { generation.current++; setDraft(value => ({ ...value, ...patch })); setPreview(undefined); setNote(''); };
  async function selectFile(file?: File) {
    if (!file) return;
    const attempt = ++generation.current;
    setPreview(undefined);
    try {
      if (!/\.(txt|md)$/i.test(file.name) || file.size > 65536) throw new Error('请选择不超过 64 KiB 的 .txt 或 .md UTF-8 文本');
      const content = new TextDecoder('utf-8', { fatal: true }).decode(await file.arrayBuffer());
      if (!alive.current || attempt !== generation.current) return;
      edit({ name: file.name, content, source: 'file' });
    } catch { if (alive.current && attempt === generation.current) setNote('文件不可导入，请选择不超过 64 KiB 的 .txt 或 .md UTF-8 文本'); }
  }
  async function prepare() {
    setPreparing(true); setNote('');
    const attempt = generation.current;
    try {
      const bytes = new TextEncoder().encode(draft.content).length;
      if (!draft.content.trim() || draft.content.includes('\0') || bytes > 65536 ||
          !draft.reason.trim() || draft.name.length > 120 || !/^[^/\\:\x00-\x1f]+\.(txt|md)$/i.test(draft.name))
        throw new Error('请填写非空文本、有效 .txt/.md 名称和授权依据；正文最多 64 KiB');
      await command.verifyScope();
      const fresh = checkMaterials(await api.coreMaterials(scope.organizationId), scope);
      if (!fresh.access.can_manage || fresh.version !== read.version) throw new Error('资料许可或组织版本已变化，请关闭后刷新核对；输入暂时保留');
      const sha256 = await digest(draft.content);
      await command.verifyScope();
      if (!alive.current || attempt !== generation.current) return;
      setPreview({ ...draft, id: 'material-' + crypto.randomUUID().replaceAll('-', ''), bytes, sha256, version: fresh.version });
    } catch (error) {
      if (alive.current) {
        if (accessLost(error)) { edit({content: ''}); onAccessLost(); }
        else if (attempt === generation.current) setNote(errorText(error));
      }
    }
    finally { if (alive.current) setPreparing(false); }
  }
  return <Dialog id="material-dialog" title="导入业务资料并授权只读" closeId="close-material" onClose={onClose}>
    <p>只保存这份正文并允许本组织工作只读；不调用模型，不访问其他文件。</p>
    {command.reference ? <div role="status">
      {command.reference.originServiceInstance && command.reference.originServiceInstance !== scope.serviceInstance &&
        <p>原宿主进程已更换；请查询原请求核对导入结果。</p>}
      <p>{command.note || '原导入请求已保留；请核对结果，不要重复导入。'}</p>
      <button className="button secondary" disabled={command.checking} onClick={() => void command.lookup()}>查询导入原请求</button>
      {command.reference.resolved && <button className="button secondary" onClick={() => {
        command.another(); setPreview(undefined);
      }}>修改后再次预览</button>}
    </div> : <>
      <label className="operation-field">选择 UTF-8 文本文件<input type="file" accept=".txt,.md" onChange={e => void selectFile(e.target.files?.[0])} /></label>
      <label className="operation-field">资料名称<input maxLength={120} value={draft.name} onChange={e => edit({ name: e.target.value })} /></label>
      <label className="operation-field" htmlFor="business-material-body">业务资料正文</label>
      <textarea id="business-material-body" rows={7} value={draft.content} onChange={e => edit({ content: e.target.value, source: 'paste' })} />
      <label className="operation-field" htmlFor="business-material-reason">资料授权依据</label>
      <textarea id="business-material-reason" maxLength={10000} rows={2} value={draft.reason} onChange={e => edit({ reason: e.target.value })} />
      {preview ? <div className="material-preview">
        <h3>核对这份业务资料</h3><p>{preview.name} · {preview.bytes} 字节 · 来源：{preview.source === 'file' ? '选择文件' : '粘贴文本'}</p>
        <p>版本 1 · 本组织只读 · SHA-256 {preview.sha256}</p><pre>{preview.content}</pre>
        <button className="button primary" disabled={command.sending || command.blocked} onClick={() => void command.send({
          material_id: preview.id, name: preview.name, content: preview.content, source: preview.source, reason: preview.reason,
        }, preview.version, async () => {
          const fresh = checkMaterials(await api.coreMaterials(scope.organizationId), scope);
          if (!fresh.access.can_manage || fresh.version !== preview.version) throw new Error('资料许可或版本已变化，尚未提交；输入保留');
        })}>确认导入并授权只读</button>
      </div> : <button className="button primary" disabled={preparing || command.blocked} onClick={() => void prepare()}>预览资料与授权</button>}
    </>}
    {(note || (!command.reference && command.note)) && <p role="alert">{note || command.note}</p>}
    <p className="form-note">每份最多 64 KiB，共 16 份、总计 1 MiB；已撤销历史保留。未提交内容只在当前窗口内，关闭即丢弃。</p>
    <button className="button secondary" onClick={onClose}>返回资料列表</button>
  </Dialog>;
}

function MaterialPermission({ item, read, scope, onAccessLost }: {
  item: BusinessMaterial; read: CoreMaterials; scope: WorkScope; onAccessLost: () => void;
}) {
  const [reason, setReason] = useState('');
  const command = useWorkCommand(scope, onAccessLost, { kind: 'revoke_material', materialId: item.id,
    version: item.version, sha256: item.sha256 });
  return <>
    {read.access.can_manage && item.read_allowed && !command.reference && <details>
      <summary>撤销这份资料的只读许可</summary>
      <p>后续读取和原工具上下文再发送将拒绝；已发生的调用、原工作及资料历史保留。</p>
      <label>撤销依据<input maxLength={10000} value={reason} onChange={e => setReason(e.target.value)} /></label>
      <button className="button secondary" disabled={!reason.trim() || command.sending || command.blocked}
        onClick={() => void command.send({ material_id: item.id, expected_version: item.version, reason }, read.version, async () => {
          const fresh = checkMaterials(await api.coreMaterials(scope.organizationId), scope);
          const current = fresh.materials.find(value => value.id === item.id);
          if (!fresh.access.can_manage || !current?.read_allowed || current.version !== item.version || current.sha256 !== item.sha256)
            throw new Error('资料许可或版本已变化，请刷新核对');
        })}>确认撤销只读许可</button>
    </details>}
    {command.note && <p role="status">{command.note}</p>}
    {command.reference && <button className="button secondary" disabled={command.checking} onClick={() => void command.lookup()}>查询撤权原请求</button>}
  </>;
}

export function MaterialsPanel({ scope, onAccessLost }: { scope: WorkScope; onAccessLost: () => void }) {
  const read = useMaterials(scope);
  const [importing, setImporting] = useState(false);
  return <section className="business-materials" aria-label="业务资料">
    <h2>业务资料</h2><p>将明确选择的资料交给本组织工作；模型连接验证附件不会自动成为业务资料。</p>
    {read.isPending ? <p role="status">正在读取资料许可…</p> : read.error || !read.data ?
      <p role="alert">资料暂不可读取；{errorText(read.error)}，请刷新重试。</p> : <>
      <button className="button primary" disabled={!read.data.access.can_manage} onClick={() => setImporting(true)}>选择或粘贴业务资料</button>
      {!read.data.access.can_manage && <p>须有权治理者在有效治理下确认资料授权；已有记录仍保留。</p>}
      {!read.data.materials.length && <p>尚未导入业务资料。</p>}
      <ul className="material-list">{read.data.materials.map(item => <li key={item.id}>
        <h3>{item.name}</h3><p>{item.read_allowed ? '本组织只读' : '已撤销后续读取'} · 版本 {item.version} · {item.bytes} 字节</p>
        <p>来源：{item.source === 'file' ? '选择文件' : '粘贴文本'} · SHA-256 {item.sha256}</p>
        <MaterialPermission item={item} read={read.data!} scope={scope} onAccessLost={onAccessLost} />
      </li>)}</ul>
      {importing && <MaterialImport scope={scope} read={read.data} onClose={() => setImporting(false)} onAccessLost={onAccessLost} />}
    </>}
    <button className="button secondary" disabled={read.isFetching} onClick={() => void read.refetch()}>刷新业务资料</button>
    <Link className="button secondary" to={organizationPath(scope.organizationId, 'work')}>在工作中选择资料</Link>
  </section>;
}

export function CoreMaterials() {
  const workspace = useWorkspace();
  const [lost, setLost] = useState(false);
  const session = workspace.session;
  if (!workspace.core || !session?.principal_id || !session.service_instance) return null;
  if (lost) return <p role="alert">资料权限或身份已变化，请刷新当前组织后重开。</p>;
  const scope = { organizationId: workspace.core.au.id, principalId: session.principal_id, serviceInstance: session.service_instance };
  return <MaterialsPanel key={JSON.stringify(scope)} scope={scope} onAccessLost={() => setLost(true)} />;
}

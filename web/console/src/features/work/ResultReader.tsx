import {useEffect, useRef, useState} from 'react';
import {Link} from 'react-router-dom';
import {api, ApiError, errorText} from '../../api/client';
import {organizationPath} from '../../app/organization-routes';
import type {CoreWorkItem, CoreWorkResult, CoreWorkResultContent} from '../../api/types';
import type {WorkScope} from './useWorkCommand';
import {checkResultSession, checkedResult, readResultWork} from './result-reading';

export function ResultReader({scope, work, result, onRefresh}: {scope: WorkScope; work: CoreWorkItem; result: CoreWorkResult; onRefresh: () => Promise<unknown>}) {
  const [value, setValue] = useState<CoreWorkResultContent>();
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(false);
  const [revision, setRevision] = useState(0);
  const [denied, setDenied] = useState(false);
  const pending = useRef<AbortController | undefined>(undefined);
  useEffect(() => {
    const controller = new AbortController(); pending.current = controller;
    setValue(undefined); setError(''); setLoading(true);
    void checkedResult(scope, work, result, controller.signal).then(body => {
      controller.signal.throwIfAborted(); setValue(body);
    }).catch(e => {if (!controller.signal.aborted) {
      setError(errorText(e));
      if (e instanceof ApiError && [401, 403].includes(e.status ?? 0)) setDenied(true);
    }})
      .finally(() => {if (!controller.signal.aborted) setLoading(false);});
    return () => {controller.abort(); pending.current?.abort();};
  }, [revision]); // The parent keys this component by scope, Work and result version.

  async function refresh() {
    pending.current?.abort(); setValue(undefined); setError(''); setLoading(true);
    await onRefresh();
    setDenied(false);
    setRevision(x => x + 1);
  }

  async function download() {
    pending.current?.abort();
    const controller = new AbortController(); pending.current = controller;
    setDownloading(true); setError('');
    try {
      const read = await readResultWork(scope, controller.signal);
      const current = read.works.find(x => x.id === work.id);
      const version = current?.results.find(x => x.id === result.id);
      if (!current || !version || version.seq !== result.seq || version.sha256 !== result.sha256)
        throw new Error('原成果版本已变化，请刷新核对');
      const body = await checkedResult(scope, current, version, controller.signal);
      checkResultSession(await api.session(controller.signal), scope);
      controller.signal.throwIfAborted();
      const url = URL.createObjectURL(new Blob([body.content], {type:'text/plain;charset=utf-8'}));
      try {
        const link = document.createElement('a'); link.href = url;
        link.download = `${work.id}-${result.id}-v${result.seq}.txt`; link.click();
      } finally {URL.revokeObjectURL(url);}
    } catch (e) {
      if (!controller.signal.aborted) {
        setValue(undefined); setError(errorText(e));
        if (e instanceof ApiError && [401, 403].includes(e.status ?? 0)) setDenied(true);
      }
    } finally {if (!controller.signal.aborted) setDownloading(false);}
  }

  if (denied) return <section><p role="alert">{error}</p>
    <button className="button secondary" disabled={loading || downloading} onClick={() => void refresh()}>刷新成果</button></section>;
  return <article className="core-result-reader">
    <h1>{result.title}</h1><p>来源工作：{work.title} · 版本 {result.seq}</p>
    <p>{result.status === 'adopted' ? '已采用' : '候选'}</p>
    {work.status === 'delivered' && work.delivered_result_id === result.id && <p>已交付</p>}
    <dl className="result-provenance">
      <div><dt>产生时间</dt><dd>{result.created_at}</dd></div>
      <div><dt>采用主体与时间</dt><dd>{result.adopted_by_principal_id ? `${result.adopted_by_principal_id} · ${result.adopted_at}` : '尚未采用'}</dd></div>
      {work.delivered_result_id === result.id && <div><dt>交付依据</dt><dd>此版本已被原工作采用并交付 · {work.delivered_at}</dd></div>}
      <div><dt>来源依据</dt><dd>{result.sources.length ? result.sources.join('、') : '未记录来源'}</dd></div>
      {result.input_cursor !== undefined && <div><dt>补充输入依据</dt><dd>
        <span>{result.input_cursor ? `采用至输入 ${result.input_cursor}` : '生成此成果时尚无已采用的补充输入'}</span>
        {result.input_step_ref && <p>原步骤 {result.input_step_ref}{result.input_refs?.length ? ` · 本步附入 ${result.input_refs.join('、')}` : ''}</p>}
      </dd></div>}
      <div><dt>正文校验</dt><dd>UTF-8 {result.bytes} 字节 · SHA-256 {result.sha256}</dd></div>
    </dl>
    {loading && <p role="status">正在读取并校验成果正文…</p>}
    {error && <p role="alert">{error}</p>}
    {value && <><div className="result-body" role="region" aria-label="成果正文">{value.content}</div>
      <button className="button primary" disabled={downloading} onClick={() => void download()}>{downloading ? '正在核对下载权限…' : '下载正文'}</button></>}
    <div className="result-reader-actions"><button className="button secondary" disabled={loading || downloading} onClick={() => void refresh()}>刷新成果</button>
      <Link className="button secondary" to={`${organizationPath(scope.organizationId, 'work')}/${encodeURIComponent(work.id)}`}>返回原工作</Link></div>
  </article>;
}

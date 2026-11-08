import type { CoreWorkItem, CoreWorkResult } from '../../api/types';
import { useWorkCommand, type WorkScope, type ResultCommandTarget } from './useWorkCommand';
import './result-delivery.css';

function ResultAction({
  scope,
  item,
  result,
  kind,
  version,
  canManage,
  onAccessLost,
}: {
  scope: WorkScope;
  item: CoreWorkItem;
  result: CoreWorkResult;
  kind: ResultCommandTarget['kind'];
  version: number;
  canManage: boolean;
  onAccessLost: () => void;
}) {
  const command = useWorkCommand(scope, onAccessLost, {
    kind,
    workId: item.id,
    resultId: result.id,
    sha256: result.sha256,
  });
  const adopting = kind === 'adopt_result';
  const eligible = adopting
    ? result.status === 'candidate'
    : result.status === 'adopted' &&
      ['pending', 'running', 'waiting'].includes(item.status) &&
      !item.attempts.some((a) => a.status === 'running');
  async function submit() {
    await command.send({ work_id: item.id, result_id: result.id }, version, async (read) => {
      const current = read.works.find((w) => w.id === item.id);
      const candidate = current?.results.find((r) => r.id === result.id);
      if (
        !current ||
        !candidate ||
        candidate.sha256 !== result.sha256 ||
        candidate.status !== (adopting ? 'candidate' : 'adopted') ||
        JSON.stringify(candidate.sources) !== JSON.stringify(result.sources)
      )
        throw new Error('原成果或来源已变化，请刷新核对后提交');
      if (
        !adopting &&
        (!['pending', 'running', 'waiting'].includes(current.status) ||
          current.attempts.some((a) => a.status === 'running'))
      )
        throw new Error('工作状态已变化或仍有执行未结束，请刷新核对');
    });
  }
  return (
    <div className="work-actions">
      {eligible && canManage && !command.reference && (
        <button type="button" disabled={command.sending || command.blocked} onClick={submit}>
          {adopting ? '采用此成果' : '交付此成果'}
        </button>
      )}
      {command.reference && (
        <>
          <span className="form-note">
            {adopting ? '采用' : '交付'}原请求：{command.reference.id}
          </span>
          <button type="button" disabled={command.checking} onClick={command.lookup}>
            {adopting ? '查询采用原请求' : '查询交付原请求'}
          </button>
          {command.reference.resolved &&
            command.reference.outcome === 'rejected' &&
            eligible &&
            canManage && (
              <button
                type="button"
                disabled={command.sending || command.checking}
                onClick={command.another}
              >
                {adopting ? '重新核对采用' : '重新核对交付'}
              </button>
            )}
        </>
      )}
      {command.note && (
        <p role="status" className="form-note">
          {command.note}
        </p>
      )}
    </div>
  );
}

/** Keep both command lifetimes mounted across candidate/adopted/delivered transitions. */
export function CoreResultDelivery(props: {
  scope: WorkScope;
  item: CoreWorkItem;
  version: number;
  canManage: boolean;
  onAccessLost: () => void;
}) {
  return (
    <div className="work-result-delivery" aria-label="成果采用与交付">
      {props.item.status === 'delivered' && <p>工作已交付</p>}
      {props.item.results.map((result) => (
        <section key={result.id} aria-label={'成果 ' + result.id}>
          <p className="form-note">
            成果：{result.id} · SHA256：{result.sha256}
          </p>
          <p className="form-note">
            来源：{result.sources.length ? result.sources.join('、') : '未记录来源'}
          </p>
          {(['adopt_result', 'deliver_work'] as const).map((kind) => (
            <ResultAction key={kind} {...props} result={result} kind={kind} />
          ))}
        </section>
      ))}
    </div>
  );
}

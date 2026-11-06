import { useState } from 'react';
import { isGovernedAU } from '../../api/core-boundary';
import { Area, Field } from '../commands/form-fields';
import type { GovernanceDraft } from './model';
import { ResponsibilityFields } from './ResponsibilityFields';
import { DecisionReason, PrincipalField } from './fields';

export function GovernanceFields({ draft }: { draft: GovernanceDraft }) {
  const governance = isGovernedAU(draft.read) ? draft.read.au.governance : undefined;
  const [mode, setMode] = useState(governance?.unavailability.mode ?? 'exit_after_timeout');
  const [cancelNomination, setCancelNomination] = useState(false);
  switch (draft.kind) {
    case 'adopt_governance':
    case 'configure_governance':
      return (
        <>
          <p>最终决定方为当前治理者。章程、目标、资源、任职、授权与解散均为保留事项。</p>
          <label className="operation-field">
            失能处理方式
            <select
              name="unavailability_mode"
              value={mode}
              onChange={(event) => setMode(event.target.value as typeof mode)}
            >
              <option value="exit_after_timeout">到期后退出（适用于单主体）</option>
              <option value="successor_after_timeout">到期后由已确认的后继者接任</option>
            </select>
          </label>
          <Field
            name="timeout_seconds"
            label="有效期（秒）"
            type="number"
            min={60}
            max={2678400}
            step={1}
            value={governance?.unavailability.timeout_seconds ?? 86400}
          />
          {mode === 'successor_after_timeout' && (
            <>
              <PrincipalField
                name="successor_principal_id"
                label="后继者核心身份标识"
                value={governance?.unavailability.successor_principal_id}
              />
              <p className="form-note">
                由对方在“账号与登录”复制稳定标识。采用后，对方还须自行确认恢复职责。
              </p>
            </>
          )}
          <DecisionReason />
        </>
      );
    case 'nominate_governor':
      return (
        <>
          {governance?.nomination && (
            <label className="check-field">
              <input
                type="checkbox"
                name="cancel_nomination"
                checked={cancelNomination}
                onChange={(event) => setCancelNomination(event.target.checked)}
              />
              取消当前提名
            </label>
          )}
          <PrincipalField
            name="principal_id"
            label="接任者核心身份标识"
            value={governance?.nomination?.principal_id}
            disabled={cancelNomination}
          />
          <p className="form-note">
            请使用对方已登记账号的稳定标识。姓名或宿主账号不会替代接任者确认。
          </p>
          <DecisionReason />
        </>
      );
    case 'set_goal':
      return (
        <>
          <Area name="goal" label="AU目标" value={draft.read.au.goal} />
          <DecisionReason />
        </>
      );
    case 'amend_charter':
      return (
        <>
          <Area name="charter_text" label="章程正文" value={draft.read.au.charter.text} rows={6} />
          <label className="check-field">
            <input
              name="record_memory"
              type="checkbox"
              defaultChecked={draft.read.au.charter.allowed_operations.includes('record_memory')}
            />
            允许内部文字记录
          </label>
          <label className="check-field">
            <input
              name="read_document"
              type="checkbox"
              defaultChecked={draft.read.au.charter.allowed_tools.includes('read_document')}
            />
            允许只读所选验证资料
          </label>
          <p className="form-note">
            仅允许模型接入验证读取明确选择的文本资料，不授予宿主文件访问或其他工具权限。
          </p>
          <label className="check-field">
            <input
              name="board_can_amend"
              type="checkbox"
              defaultChecked={draft.read.au.charter.board_can_amend}
            />
            允许修订章程
          </label>
          <p className="form-note">
            保留其余已存的操作、工具和保留事项字段。本地治理仅执行已支持的规则，正文不隐式授权。
          </p>
          <DecisionReason />
        </>
      );
    case 'acknowledge_recovery':
    case 'activate_governance':
    case 'renew_governance':
    case 'accept_governance':
    case 'recover_governance':
    case 'exit_governance':
      return <DecisionReason />;
    default:
      return <ResponsibilityFields draft={draft} />;
  }
}

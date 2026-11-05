import { useState } from 'react';
import { Area, Field, Rules } from './form-fields';
import { defaultCharter, novelCharter } from './model';

export function CreationFields({ core }: { core: boolean }) {
  const [template, setTemplate] = useState('generic');
  return (
      <>
        {!core && <label className="operation-field">
          创建类型
          <select
            name="company_template"
            value={template}
            onChange={(e) => setTemplate(e.target.value)}
          >
            <option value="generic">旧版通用试验 · 兼容运行时</option>
            <option value="novel">小说公司 · 三周期首版（旧版兼容）</option>
          </select>
        </label>}
        {core && <p className="form-note">初始治理主体由当前登录账户绑定。显示名称不授予权限；创建只保存准备态和资源计划。</p>}
        <Field
          key={template + '-name'}
          name="name"
          label={core ? 'AU名称' : '公司名称'}
          value={core ? '我的 AU' : template === 'novel' ? '我的 AI 小说公司' : '我的 AI 公司'}
          maxLength={200}
        />
        <Area
          key={template + '-goal'}
          name="goal"
          label={core ? 'AU目标' : '公司目标'}
          value={
            template === 'novel'
              ? '自主组织团队，创作同一本中文网络小说并连续交付三章；向模拟平台投稿，核算成本，依据反馈调整后续创作。'
              : ''
          }
        />
        {template === 'novel' && (
          <>
            <Field
              name="initial_budget_minor"
              label="启动模拟预算（分，10000 = ¥100）"
              type="number"
              min={1}
              max={10000000000}
              value={10000}
            />
            <div className="field-grid">
              <Field
                name="input_price_minor_per_million"
                label="输入单价（分 / 百万 token）"
                type="number"
                min={0}
                max={10000000000}
                value={100}
              />
              <Field
                name="output_price_minor_per_million"
                label="输出单价（分 / 百万 token）"
                type="number"
                min={0}
                max={10000000000}
                value={500}
              />
            </div>
            <p className="form-note">
              单价是可编辑示例，请按供应商填写。预算为经营试验阈值；真实 API
              账单另计，单次调用可能使估算余额越限。第二章固定低订阅，用于观察后续调整。
            </p>
          </>
        )}
        <Field
          name="board_name"
          label={core ? '治理主体显示名称' : '章程采用人'}
          value={core ? '初始治理主体' : '本机发起人（本地测试采用）'}
          maxLength={200}
        />
        <Rules key={template} prepared={core} charter={template === 'novel' ? novelCharter : defaultCharter} />
        <div className="field-grid">
          <Field
            name="max_calls"
            key={template}
            label={core ? '计划调用上限' : '累计调用上限'}
            value={template === 'novel' ? 32 : 8}
            type="number"
            min={1}
            max={10000}
          />
          <Field
            name="timeout_seconds"
            label="单次超时（秒）"
            value={180}
            type="number"
            min={1}
            max={3600}
          />
        </div>
      </>
    );
}

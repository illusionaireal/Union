import type { InputHTMLAttributes, ReactNode } from 'react';
import type { Charter } from '../../api/types';
export function Field({
  name,
  label,
  value = '',
  ...props
}: InputHTMLAttributes<HTMLInputElement> & {
  name: string;
  label: string;
  value?: string | number;
}) {
  return (
    <label className="operation-field">
      {label}
      <input name={name} defaultValue={value} required {...props} />
    </label>
  );
}
export function Area({
  name,
  label,
  value = '',
  rows = 3,
}: {
  name: string;
  label: string;
  value?: string;
  rows?: number;
}) {
  return (
    <label className="operation-field">
      {label}
      <textarea name={name} defaultValue={value} rows={rows} required maxLength={100000} />
    </label>
  );
}
export function Select({
  name,
  label,
  children,
  value,
}: {
  name: string;
  label: string;
  children: ReactNode;
  value?: string;
}) {
  return (
    <label className="operation-field">
      {label}
      <select name={name} defaultValue={value}>
        {children}
      </select>
    </label>
  );
}
export function Reason() {
  return <Area name="reason" label="操作理由与核对依据" />;
}
export function Rules({ charter, prepared = false }: { charter: Charter; prepared?: boolean }) {
  const { text, ...rules } = charter;
  return (
    <>
      <Area name="charter_text" label="章程正文" value={text} />
      <details>
        <summary>受支持的规则字段</summary>
        <Area
          name="charter_rules"
          label="组织操作、工具、保留事项与修章入口"
          value={JSON.stringify(rules, null, 2)}
          rows={8}
        />
        <p className="form-note">{prepared ? '这些字段保存为初始章程内容，尚未启用为执行规则。' : '只接受已实现的规则字段；正文不隐式授予权限。'}</p>
      </details>
    </>
  );
}

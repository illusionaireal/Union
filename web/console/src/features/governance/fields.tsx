import { Field } from '../commands/form-fields';

export function DecisionReason() {
  return (
    <label className="operation-field">
      决定依据
      <textarea name="reason" rows={3} required maxLength={10000} />
    </label>
  );
}
export function PrincipalField({
  name,
  label,
  value = '',
  disabled = false,
}: {
  name: string;
  label: string;
  value?: string;
  disabled?: boolean;
}) {
  return (
    <Field
      name={name}
      label={label}
      value={value}
      disabled={disabled}
      required={!disabled}
      maxLength={100}
      autoComplete="off"
    />
  );
}

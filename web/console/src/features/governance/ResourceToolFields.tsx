import { DecisionReason } from './fields';

/** The resource journey proposes one change under the existing charter rules. */
export function ResourceToolFields() {
  return <>
    <p>仅允许模型接入验证读取明确选择的文本；不授予宿主文件访问或业务资料许可。</p>
    <p>本次只增加只读验证工具，保留原章程正文、其他工具与操作、修章资格和保留事项。按当前有效规则核对并确认后才采用。</p>
    <DecisionReason />
  </>;
}

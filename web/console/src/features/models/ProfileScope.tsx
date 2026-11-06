import { Card } from '../../components/ui';
import type { CapabilityStatus, ModelRead, ProfileCapability } from './types';

const statusLabel: Record<CapabilityStatus, string> = {
  verified_real: '真实已验证',
  controlled: '仅受控验证',
  unsupported: '不支持',
};

const capabilityLabel: Record<ProfileCapability, string> = {
  text_answer: '文字回答',
  tool_roundtrip: '工具往返（只读资料）',
  usage_reporting: '用量记录',
  streaming: '边生成边显示',
  long_job_new_input: '长任务期间接收新输入',
  cancel_and_query: '取消与中断后查询',
};

export function ProfileScope({ read }: { read: ModelRead }) {
  const profiles = read.capabilities.profiles
    .map((name) => ({ name, scope: read.capabilities.profile_scope[name] }))
    .filter((item) => item.scope);
  if (!profiles.length) return null;
  return (
    <Card title="各接入方式的能力范围">
      <p>
        一种接入方式通过验证，不代表其他方式可用。未验证或被判定不支持的项目会如实标出。
      </p>
      {profiles.map(({ name, scope }) => (
        <section key={name} className="profile-scope">
          <h3>{scope.title}</h3>
          <p className="security-note">
            {scope.auth === 'api_key' ? '需要自己的 API 密钥' : '需要本 AU 的模型服务授权'}
          </p>
          <dl className="au-facts">
            {(Object.keys(capabilityLabel) as ProfileCapability[]).map((key) => {
              const claim = scope.capabilities[key];
              if (!claim) return null;
              return (
                <div key={key}>
                  <dt>{capabilityLabel[key]}</dt>
                  <dd>
                    {statusLabel[claim.status]}
                    {claim.status !== 'unsupported' && claim.evidence && (
                      <small>（{claim.evidence}）</small>
                    )}
                  </dd>
                  <dd>
                    <small>{claim.note}</small>
                  </dd>
                </div>
              );
            })}
          </dl>
        </section>
      ))}
    </Card>
  );
}

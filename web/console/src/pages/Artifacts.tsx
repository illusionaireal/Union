import { ShieldCheck } from 'lucide-react';
import { useWorkspace } from '../app/workspace';
import { ArtifactRows } from '../components/Records';
import { Card } from '../components/ui';
import { PageStats } from '../components/SetupGuide';
export default function Artifacts() {
  const { data } = useWorkspace();
  return (
    <>
      <PageStats
        items={[
          { label: '成果版本', value: Object.keys(data!.organization.artifacts).length },
          {
            label: '来源工作',
            value: new Set(Object.values(data!.organization.artifacts).map((a) => a.work_id)).size,
          },
          { label: '文件验证', value: '打开时核验', note: '保留来源与历史版本' },
        ]}
      />
      <div className="inline-note">
        <ShieldCheck size={19} />
        <p>每份成果保留版本、负责成员与来源工作。打开时读取实际文件并校验 SHA-256。</p>
      </div>
      <Card title="全部成果版本">
        <ArtifactRows artifacts={Object.values(data!.organization.artifacts)} />
      </Card>
    </>
  );
}

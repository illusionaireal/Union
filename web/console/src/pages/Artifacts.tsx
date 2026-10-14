import { ShieldCheck } from 'lucide-react';
import { useWorkspace } from '../app/workspace';
import { ArtifactRows } from '../components/Records';
import { Card } from '../components/ui';
export default function Artifacts() {
  const { data } = useWorkspace();
  return (
    <>
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

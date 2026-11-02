"""Import explicitly checked-out models.dev metadata without copying credentials/endpoints."""
import argparse
import io
import json
import math
import subprocess
import tarfile
import tomllib
from pathlib import Path


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('upstream', type=Path)
    args=parser.parse_args()
    git=['git','-c','core.protectNTFS=false','-C',str(args.upstream)]
    revision=subprocess.check_output(git+['rev-parse','HEAD'],text=True).strip()
    # Archive is consumed in memory, never extracted: upstream colon-containing
    # model IDs cannot be represented as Windows filenames.
    archive=subprocess.check_output(git+['archive','HEAD','providers','LICENSE'])
    records=[]
    with tarfile.open(fileobj=io.BytesIO(archive)) as source:
        license_bytes=source.extractfile('LICENSE').read()
        for entry in source.getmembers():
            parts=entry.name.split('/')
            if len(parts)<4 or parts[0]!='providers' or parts[2]!='models' or not entry.name.endswith('.toml'): continue
            data=tomllib.loads(source.extractfile(entry).read().decode())
            record={'provider':parts[1], 'model':'/'.join(parts[3:])[:-5], 'source':'https://github.com/anomalyco/models.dev', 'revision':revision}
            limits=data.get('limit',{})
            for name,key in [('context_window','context'),('max_output_tokens','output')]:
                if type(limits.get(key)) is int and limits[key]>0: record[name]=limits[key]
            if record.get('max_output_tokens',0)>record.get('context_window',10**12): record.pop('max_output_tokens',None)
            caps=data.get('capabilities',{})
            for name,key in [('tool_call','tools'),('reasoning','reasoning')]:
                value=caps.get(key,{})
                value=value.get('supported') if isinstance(value,dict) else value
                if type(value) is bool: record[name]=value
            for key,target in [('input','input_modalities'),('output','output_modalities')]:
                values=[]
                for item in data.get('modalities',{}).get(key,[]):
                    kind='pdf' if item=='application/pdf' else item.split('/')[0]
                    if kind in {'text','image','audio','video','pdf'} and kind not in values: values.append(kind)
                if values: record[target]=values
            # models.dev schema-v2 declares USD per 1M text tokens. Preserve
            # scalar base quotes only, never infer tier/region/cache overrides.
            costs={}
            for direction in ('input','output'):
                quote=data.get('cost',{}).get('text',{}).get(direction,{})
                price=quote.get('price') if isinstance(quote,dict) and quote.get('unit','token')=='token' else None
                if type(price) in (int,float) and math.isfinite(price) and price>=0: costs[direction]=price
            if costs:record['cost']=costs
            records.append(record)
    from ai_union.catalog import Catalog
    Catalog(records)
    target=Path(__file__).resolve().parents[1]/'data'
    target.mkdir(exist_ok=True)
    (target/'model-catalog.json').write_text(json.dumps({'version':1,'models':records},ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
    (target/'models-dev-LICENSE.txt').write_bytes(license_bytes)
    (target/'MODEL_CATALOG.md').write_text(f'# 模型目录快照\n\n来源：https://github.com/anomalyco/models.dev ，revision `{revision}`，导入日期2026-11-02。\n\n{len(records)}条记录、{len(set(r["provider"] for r in records))}个供应商。转换明确声明的能力/模态/上下文，以及schema-v2中每百万文本token的USD基础参考单价；未知/阶梯/区域/服务档位价格不推断。目录不包含凭据或API地址，不推断账户权限；上游参考价格不自动成为计费依据。\n\n保留MIT数据许可见models-dev-LICENSE.txt，本数据许可不改变UNION仓库许可。默认离线加载；UNION_MODEL_CATALOG可指定替代快照。\n',encoding='utf-8')
    print(f'Imported {len(records)} records at {revision}')


if __name__=='__main__': main()

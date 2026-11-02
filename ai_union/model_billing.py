"""Usage-based estimates and immutable period allocations, never payment execution."""
import hashlib
import json
import re
from .engine import encoded, identifier, now, require, text

BASES=('metered','subscription','owned','unknown')
RATE_FIELDS=('input_per_million_minor','output_per_million_minor','cache_read_per_million_minor')


def validate_billing(value):
    require(isinstance(value,dict) and set(value)<={'basis','currency','revision',*RATE_FIELDS}, '费用口径字段无效')
    require(value.get('basis') in BASES, '费用口径不支持')
    if 'currency' in value: require(isinstance(value['currency'],str) and re.fullmatch(r'[A-Z]{3}',value['currency']), '币种必须是三位大写代码')
    if 'revision' in value: identifier(value['revision'])
    for key in RATE_FIELDS:
        if key in value: require(type(value[key]) is int and 0<=value[key]<=10**12, '费率须为非负整数最小货币单位')
    if value['basis']=='metered':
        require({'currency','revision','input_per_million_minor','output_per_million_minor'}<=set(value), '按量估算须配置币种、费率版本与输入输出单价')


def calculate(billing, usage):
    billing=billing or {'basis':'unknown'}
    validate_billing(billing)
    value={'cost_basis':billing['basis'],'cost_minor':None,'cost':None,'cost_status':'unknown', 'currency':billing.get('currency'),'billing_revision':billing.get('revision')}
    inp,out=usage.get('input_tokens'),usage.get('output_tokens')
    if billing['basis']=='metered' and type(inp) is int and type(out) is int and inp>=0 and out>=0:
        cached=usage.get('cached_input_tokens',0)
        if type(cached) is not int or not 0<=cached<=inp: return value
        numerator=(inp-cached)*billing['input_per_million_minor']+out*billing['output_per_million_minor']+cached*billing.get('cache_read_per_million_minor',billing['input_per_million_minor'])
        amount=(numerator+999999)//1000000
        value.update(cost_minor=amount,cost=amount,cost_status='estimated')
    return value


def distribute(amount, weights):
    require(type(amount) is int and 0<=amount<=10**15, '分摊金额须为非负整数最小货币单位')
    require(weights and all(type(v) is int and v>0 for v in weights.values()), '分摊须有可核实的正数用量权重')
    total=sum(weights.values()); result={k:amount*v//total for k,v in weights.items()}
    ranked=sorted(weights,key=lambda k:(-(amount*weights[k]%total),k))
    for key in ranked[:amount-sum(result.values())]:result[key]+=1
    return result


def allocate(engine, key, voucher, reason):
    text(reason, '分摊依据', 1000)
    require(isinstance(voucher,dict) and set(voucher)=={'id','basis','currency','period','amount_minor','run_ids'}, '分摊凭证字段无效')
    identifier(voucher['id']);identifier(voucher['period'])
    require(voucher['basis'] in ('subscription','owned'), '仅订阅或自有资源使用期末分摊')
    validate_billing({'basis':voucher['basis'],'currency':voucher['currency']})
    ids=voucher['run_ids']; require(isinstance(ids,list) and 0<len(ids)<=1000 and all(isinstance(rid,str) for rid in ids) and len(set(ids))==len(ids), '分摊调用列表无效或重复')
    for rid in ids:identifier(rid)
    digest=hashlib.sha256(encoded(voucher).encode()).hexdigest()
    with engine.transaction() as cx:
        board=engine._board(cx,key)
        cx.execute('CREATE TABLE IF NOT EXISTS model_cost_vouchers(id TEXT PRIMARY KEY,digest TEXT NOT NULL,data TEXT NOT NULL)')
        cx.execute('CREATE TABLE IF NOT EXISTS model_cost_allocations(run_id TEXT PRIMARY KEY,voucher_id TEXT NOT NULL,amount_minor INTEGER NOT NULL,currency TEXT NOT NULL)')
        previous=cx.execute('SELECT * FROM model_cost_vouchers WHERE id=?',(voucher['id'],)).fetchone()
        if previous:
            require(previous['digest']==digest,'分摊凭证ID冲突')
            return json.loads(previous['data'])
        weights={}
        for rid in ids:
            require(not cx.execute('SELECT 1 FROM model_cost_allocations WHERE run_id=?',(rid,)).fetchone(),'调用已经分摊，不能重复记账')
            run=engine._run(cx,rid)
            require(run['status'] in ('delivered','continued','failed'),'在途或未知执行不能分摊')
            usage=json.loads(run['usage'] or '{}')
            require(usage.get('cost_basis')==voucher['basis'],'调用成本口径与分摊不一致')
            require(usage.get('currency') in (None,voucher['currency']), '分摊币种与原调用不一致')
            weight=usage.get('elapsed_ms') if voucher['basis']=='owned' else usage.get('input_tokens',0)+usage.get('output_tokens',0)
            require(type(weight) is int and weight>0,'调用缺少分摊权重')
            weights[rid]=weight
        amounts=distribute(voucher['amount_minor'],weights)
        record={**voucher,'allocations':amounts,'cost_status':'amortized','created_at':now(),'board':board,'reason':reason}
        cx.execute('INSERT INTO model_cost_vouchers VALUES(?,?,?)',(voucher['id'],digest,encoded(record)))
        for rid,amount in amounts.items():cx.execute('INSERT INTO model_cost_allocations VALUES(?,?,?,?)',(rid,voucher['id'],amount,voucher['currency']))
        state=engine._state(cx);state['version']+=1
        engine._event(cx,'model_cost_allocated',{'voucher_id':voucher['id'],'basis':voucher['basis'],'amount_minor':voucher['amount_minor'],'currency':voucher['currency']})
        engine._save(cx,state)
        return record


def vouchers(engine):
    with engine.read_transaction() as cx:
        if not cx.execute("SELECT 1 FROM sqlite_master WHERE name='model_cost_vouchers'").fetchone():return []
        return [json.loads(row[0]) for row in cx.execute('SELECT data FROM model_cost_vouchers ORDER BY rowid DESC LIMIT 100')]

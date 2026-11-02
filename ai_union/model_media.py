"""Explicit inline media in board events; no host paths, URLs or wider member visibility."""
import base64
import json
from .engine import encoded, require

MIMES={'image/png','image/jpeg','image/webp','image/gif','application/pdf'}


def payload(content):
    require(isinstance(content,str) and len(content)<=100000, '多模态事件内容过大')
    try:value=json.loads(content)
    except (ValueError,TypeError):require(False,'多模态事件必须是有效JSON资料')
    require(isinstance(value,dict) and set(value)=={'text','attachments'}, '多模态资料字段无效')
    require(isinstance(value['text'],str) and len(value['text'])<=8000, '资料说明最多8000字符')
    require(isinstance(value['attachments'],list) and 1<=len(value['attachments'])<=4, '一次可添加1至4份资料')
    size=0; result=[]
    for item in value['attachments']:
        require(isinstance(item,dict) and set(item)=={'name','mime','data'}, '资料不能包含外部URL或宿主路径')
        require(isinstance(item['name'],str) and 0<len(item['name'])<=100 and all(c not in item['name'] for c in '/\\\x00'), '资料文件名无效')
        require(item['mime'] in MIMES and isinstance(item['data'],str), '仅支持PNG/JPEG/WebP/GIF/PDF资料')
        try:decoded=base64.b64decode(item['data'],validate=True)
        except (ValueError,TypeError):require(False,'资料base64无效')
        require(decoded, '资料不能为空')
        size+=len(decoded);require(size<=49152,'一次资料总大小不能超过48KiB')
        result.append((item,decoded))
    return value,result


def project_event(content):
    value,items=payload(content)
    return encoded({'text':value['text'],'attachments':[{'name':item['name'],'mime':item['mime'],'bytes':len(raw)} for item,raw in items]})


def attach_visible_media(package, body):
    parts=[]
    for event in package.get('context',{}).get('events',[]):
        if event.get('kind')!='model_input':continue
        _,items=payload(event['data']['content'])
        for item,raw in items:
            url='data:'+item['mime']+';base64,'+item['data']
            parts.append({'type':'file','file':{'filename':item['name'],'file_data':url}} if item['mime']=='application/pdf' else {'type':'image_url','image_url':{'url':url}})
    if parts:
        # Only events already in this acting member's host-bound package are
        # eligible. This never reads other AU records or arbitrary files.
        message=next((m for m in body['messages'] if m['role']=='user'),None)
        require(message is not None and isinstance(message['content'],str),'当前工作消息不支持附加资料')
        message['content']=[{'type':'text','text':message['content']},*parts]
    return body


def guard_media(body, guard):
    for message in body.get('messages',[]):
        if not isinstance(message.get('content'),list):continue
        for part in message['content']:
            url=part.get('image_url',{}).get('url') if part.get('type')=='image_url' else part.get('file',{}).get('file_data')
            if isinstance(url,str) and ';base64,' in url:
                try:raw=base64.b64decode(url.split(';base64,',1)[1],validate=True)
                except ValueError:require(False,'资料base64无效')
                guard(raw.decode('latin1'))

import { afterEach,beforeEach,describe,expect,it,vi } from 'vitest';
import { act,cleanup,fireEvent,render,screen,waitFor } from '@testing-library/react';
import { QueryClient,QueryClientProvider } from '@tanstack/react-query';
import SubscriptionConnections from './SubscriptionConnections';
const mocks=vi.hoisted(()=>({request:vi.fn(),workspace:{session:{platform_admin:true,service_instance:'s',session_scope:'a'},connected:true}}));
vi.mock('../api/client',()=>({request:mocks.request,errorText:(e:unknown)=>String(e)}));
vi.mock('../app/workspace',()=>({useWorkspace:()=>mocks.workspace}));
let client:QueryClient;
beforeEach(()=>{
  sessionStorage.clear();mocks.workspace.session.session_scope='a';mocks.workspace.session.platform_admin=true;
  client=new QueryClient({defaultOptions:{queries:{retry:false,gcTime:0}}});
  mocks.request.mockReset();mocks.request.mockImplementation((url:string)=>url==='/api/subscriptions'?Promise.resolve({available:true,pending:[],providers:[]}):Promise.reject(Error('not found')));
});
afterEach(()=>{cleanup();client.clear();});
const tree=()=> <QueryClientProvider client={client}><SubscriptionConnections/></QueryClientProvider>;
describe('subscription configuration',()=>{
  it('does not request host account data for ordinary sessions',()=>{
    mocks.workspace.session.platform_admin=false;render(tree());expect(mocks.request).not.toHaveBeenCalled();
  });
  it('clears the key and blocks duplicate writes while original result is unknown',async()=>{
    mocks.request.mockImplementation((url:string)=>url==='/api/subscriptions'?Promise.resolve({available:true,pending:[],providers:[]}):Promise.reject(Error('timeout')));
    render(tree());const field=screen.getByLabelText('Go API Key');fireEvent.change(field,{target:{value:'test-only-key'}});
    const button=screen.getByRole('button',{name:'保存 Go 连接'});await waitFor(()=>expect(button).not.toBeDisabled());fireEvent.click(button);
    await waitFor(()=>expect(field).toHaveValue(''));await waitFor(()=>expect(screen.getByRole('alert')).toHaveTextContent('勿重复提交'));
    expect(button).toBeDisabled();expect(JSON.stringify(sessionStorage)).not.toContain('test-only-key');
  });
  it('does not display a late authorization response after switching sessions',async()=>{
    let finish!:(value:unknown)=>void;
    mocks.request.mockImplementation((url:string)=>url==='/api/subscriptions'?Promise.resolve({available:true,pending:[],providers:[]}):url==='/api/subscription-commands'?new Promise(resolve=>{finish=resolve}):Promise.reject(Error('not found')));
    const ui=render(tree());const button=screen.getByRole('button',{name:'连接 ChatGPT 订阅'});await waitFor(()=>expect(button).not.toBeDisabled());fireEvent.click(button);
    mocks.workspace.session.session_scope='b';ui.rerender(tree());
    await act(async()=>finish({receipt:{id:'old',action:'authorize_chatgpt',status:'authorizing',message:'OLD_PRIVATE_DEVICE_CODE',url:'https://auth.openai.com/codex/device'}}));
    expect(screen.queryByText('OLD_PRIVATE_DEVICE_CODE')).not.toBeInTheDocument();expect(screen.queryByText('打开官方授权页面')).not.toBeInTheDocument();
  });
  it('starts Go account authorization without asking for a key',async()=>{
    const receipt={id:'go-native',action:'authorize_go',status:'authorizing',message:'请登录',url:'https://opencode.ai/console/auth/device',instructions:'设备码：ABCD1234'};
    mocks.request.mockImplementation((url:string)=>url==='/api/subscriptions'?Promise.resolve({available:true,native_available:true,pending:[],providers:[]}):url==='/api/subscription-commands'?Promise.resolve({receipt}):Promise.resolve({receipt}));
    render(tree());const button=screen.getByRole('button',{name:'连接 OpenCode Go 账号'});await waitFor(()=>expect(button).not.toBeDisabled());fireEvent.click(button);
    await waitFor(()=>expect(screen.getByRole('link',{name:'打开官方授权页面'})).toHaveAttribute('href',receipt.url));
    const call=mocks.request.mock.calls.find(c=>c[0]==='/api/subscription-commands');expect(JSON.parse(call![1].body).action).toBe('authorize_go');expect(call![1].body).not.toContain('api_key');
  });
  it('clears callback input and never persists callback credentials',async()=>{
    const receipt={id:'chat-native',action:'authorize_chatgpt',status:'authorizing',message:'请登录',url:'https://auth.openai.com/api/accounts/authorize',needs_callback:true};
    mocks.request.mockImplementation((url:string,options?:{body:string})=>url==='/api/subscriptions'?Promise.resolve({available:true,native_available:true,pending:[],providers:[]}):url==='/api/subscription-commands'?Promise.resolve({receipt:JSON.parse(options!.body).action==='complete_chatgpt'?{...receipt,needs_callback:false}:receipt}):Promise.resolve({receipt}));
    render(tree());const button=screen.getByRole('button',{name:'连接 ChatGPT 订阅'});await waitFor(()=>expect(button).not.toBeDisabled());fireEvent.click(button);
    const field=await screen.findByLabelText('官方授权后的完整回调地址');fireEvent.change(field,{target:{value:'http://127.0.0.1:1234/auth/callback?code=PRIVATE_CALLBACK&state=state'}});
    fireEvent.click(screen.getByRole('button',{name:'完成 ChatGPT 连接'}));await waitFor(()=>expect(field).toHaveValue(''));
    expect(JSON.stringify(sessionStorage)).not.toContain('PRIVATE_CALLBACK');
    const call=mocks.request.mock.calls.find(c=>c[0]==='/api/subscription-commands'&&c[1].body.includes('complete_chatgpt'));expect(JSON.parse(call![1].body).target_id).toBe('chat-native');
  });
  it('an unknown ChatGPT request does not block Go authorization',async()=>{
    mocks.request.mockImplementation(()=>Promise.resolve({available:true,native_available:true,pending:[{id:'old',action:'authorize_chatgpt',status:'unknown',message:'待核对'}],providers:[]}));
    render(tree());await waitFor(()=>expect(screen.getByRole('button',{name:'连接 OpenCode Go 账号'})).not.toBeDisabled());expect(screen.getByRole('button',{name:'连接 ChatGPT 订阅'})).toBeDisabled();
  });
  it('keeps the last successful authorization visible after a reload',async()=>{
    mocks.request.mockImplementation((url:string)=>url==='/api/subscriptions'?Promise.resolve({available:true,native_available:true,pending:[],providers:[
      {id:'opencode-go',name:'OpenCode Go',connected:true,last_success:'2026-11-02T13:49:11.392096+00:00'},
      {id:'openai',name:'ChatGPT',connected:false,last_success:null}]}):Promise.reject(Error('not found')));
    render(tree());
    expect(await screen.findByText(/认证已保存/)).toBeVisible();
    expect(screen.getByText(/最近授权/)).toBeVisible();
  });
  it('shows the connected workspace, plan windows and Go models',async()=>{
    mocks.request.mockImplementation((url:string)=>{
      if(url==='/api/subscriptions')return Promise.resolve({available:true,native_available:true,pending:[],providers:[
        {id:'opencode-go',name:'OpenCode Go',connected:true,last_success:null},
        {id:'openai',name:'ChatGPT',connected:false,last_success:null}]});
      if(url==='/api/subscription-account')return Promise.resolve({available:true,
        workspace:{name:'Default',usage_url:'https://opencode.ai/console/wrk_1/activity/overview'},
        limits:{rolling:{percent:1,limited:false,resets_at:1793647289000},weekly:{percent:2,limited:true,resets_at:1794182400000},monthly:{percent:null,limited:false,resets_at:null}},
        accounts:[{id:'abcdef',method:'oauth'}],
        models:[{id:'go-model-a',name:'Go Model A',context:200000,output:32000,tools:true,input:['text'],status:'active'}],
        default_model:'go-model-a'});
      return Promise.reject(Error('not found'));
    });
    render(tree());
    expect(await screen.findByText(/已连接 1 个账号/)).toBeVisible();
    expect(screen.getByText(/每周 2%（已达上限）/)).toBeVisible();
    expect(screen.getByRole('link',{name:'官方用量'})).toHaveAttribute('href','https://opencode.ai/console/wrk_1/activity/overview');
    fireEvent.change(screen.getByLabelText('Go 可用模型'),{target:{value:'go-model-a'}});
    expect(screen.getByText(/上下文 200000/)).toBeVisible();
    expect(screen.getByRole('button',{name:'复制模型 ID'})).toBeVisible();
  });
});

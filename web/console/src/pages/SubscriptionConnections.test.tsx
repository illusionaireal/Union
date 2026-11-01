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
});

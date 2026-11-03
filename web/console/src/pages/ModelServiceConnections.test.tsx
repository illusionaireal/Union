import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ModelServiceConnections from './ModelServiceConnections';
const mocks=vi.hoisted(()=>({request:vi.fn(),workspace:{session:{platform_admin:true,service_instance:'service',session_scope:'session'},
  connected:true,orgId:'au-a',data:{organization:{name:'测试组织'}},refresh:vi.fn()}}));
vi.mock('../api/client',()=>({request:mocks.request,errorText:(e:unknown)=>String(e)}));
vi.mock('../app/workspace',()=>({useWorkspace:()=>mocks.workspace}));
let client:QueryClient;
beforeEach(()=>{
  sessionStorage.clear();mocks.workspace.session.platform_admin=true;
  client=new QueryClient({defaultOptions:{queries:{retry:false,gcTime:0}}});mocks.request.mockReset();
  mocks.request.mockImplementation((url:string)=>url==='/api/model-service'?Promise.resolve({available:true,accounts:[{id:'account-a',name:'Test Go',workspace:'Test'}]}):
    url.startsWith('/api/model-account-models')?Promise.resolve({models:[{id:'model-a',name:'Test Model',tools:true}]}):Promise.reject(Error('lost reply')));
});
afterEach(()=>{cleanup();client.clear();});
const tree=()=> <QueryClientProvider client={client}><ModelServiceConnections/></QueryClientProvider>;
it('does not expose or read host accounts for AU-only sessions',()=>{
  mocks.workspace.session.platform_admin=false;render(tree());expect(mocks.request).not.toHaveBeenCalled();
});
it('binds adoption to selected account, model and AU; lost reply blocks a second write',async()=>{
  render(tree());
  fireEvent.change(await screen.findByLabelText('用于当前组织的账号'),{target:{value:'account-a'}});
  const button=screen.getByRole('button',{name:'授权给 测试组织 并保存连接'});
  expect(button).toBeDisabled();
  await screen.findByRole('option',{name:'Test Model · model-a'});
  fireEvent.change(screen.getByLabelText('正式 Go 模型'),{target:{value:'model-a'}});
  expect(button).not.toBeDisabled();fireEvent.click(button);
  await waitFor(()=>expect(screen.getByRole('alert')).toHaveTextContent('勿重复提交'));
  expect(button).toBeDisabled();fireEvent.click(button);
  const writes=mocks.request.mock.calls.filter(c=>c[0]==='/api/model-account-commands');expect(writes).toHaveLength(1);
  expect(JSON.parse(writes[0][1].body)).toMatchObject({action:'adopt',organization_id:'au-a',account_ref:'account-a',model:'model-a',bind_default:true});
  expect(JSON.stringify(sessionStorage)).not.toContain('account-a');
});

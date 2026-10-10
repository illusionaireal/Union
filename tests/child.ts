import { Store, MockProvider } from '../spikes/action-safety/store.ts';
const [mode,localPath,remotePath,key,minor] = process.argv.slice(2);
const store = new Store(localPath);
const policy = {unionId:'u1',actor:'agent:u1',version:'p1',currency:'USD',target:'mock:vendor'};
try {
  store.reserve({unionId:'u1',key,actor:'agent:u1',policyVersion:'p1',currency:'USD',target:'mock:vendor',action:'mock.purchase',maxMinor:Number(minor)},policy);
  if (mode === 'crash-before-external' || mode === 'crash-after-external') {
    const action = store.claim('u1',key)!;
    if (mode === 'crash-after-external') {
      const provider = new MockProvider(remotePath);
      provider.execute(action);
      provider.close();
    }
    process.exit(42); // Exit before local receipt/settlement.
  }
  store.close();
} catch (error) {
  store.close();
  if (error instanceof Error && error.message === 'budget unavailable') process.exit(3);
  throw error;
}

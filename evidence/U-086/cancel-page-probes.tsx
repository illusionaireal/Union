// Appended to the candidate page-execution.test.tsx fixture prefix by the runner.
// Synthetic DOM only; this file is not part of the default passing test suite.
function reserved(automatic: boolean) {
  current.works[0].attempts = [
    { id: 'w1#a1', seq: 1, status: 'running', outcome: null, started_at: '', ended_at: null },
  ];
  current.works[0].budget.reserved = 1;
  current.works[0].steps = [
    { seq: 1, step_ref: 'w1#s1', attempt_id: 'w1#a1', purpose: 'work_step',
      status: 'reserved', command_id: automatic ? 'original-run' : null,
      model_request_id: automatic ? 'original-model-request' : null, at: '' },
  ];
}

it('review: the actual automatic reservation has an original-request cancel entry', async () => {
  reserved(true);
  mount();
  await screen.findByText('已登记概览');
  expect(api.coreWorkCommand).not.toHaveBeenCalled();
  expect(screen.getByRole('button', { name: '取消本次执行' })).toBeEnabled();
});

it('review: a lost cancel response retains its original lookup after reload', async () => {
  reserved(false); // Only to reach the candidate's newly added cancel handler.
  vi.mocked(api.coreWorkCommand).mockRejectedValue(new Error('cancel response lost'));
  const view = mount();
  fireEvent.click(await screen.findByRole('button', { name: '取消本次执行' }));
  await screen.findByText('cancel response lost');
  const original = vi.mocked(api.coreWorkCommand).mock.calls[0][0];
  expect(original.kind).toBe('cancel_step');
  vi.mocked(api.coreWorkReceipt).mockResolvedValue({ receipt: receipt(original) });
  view.unmount();
  mount();
  fireEvent.click(await screen.findByRole('button', { name: '查询原请求' }));
  await waitFor(() => expect(api.coreWorkReceipt).toHaveBeenCalledWith('au-1', original.id));
  expect(api.coreWorkCommand).toHaveBeenCalledTimes(1);
});

it.each(['principal_id', 'service_instance'] as const)(
  'review: cancel completion after %s changes cannot disclose the old receipt', async (field) => {
    reserved(false);
    vi.mocked(api.coreWorkCommand).mockImplementation(async (r) => {
      vi.mocked(api.session).mockResolvedValue({ ...session, [field]: 'other-scope' });
      return { receipt: { ...receipt(r), message: 'old-scope cancellation detail' } };
    });
    mount();
    fireEvent.click(await screen.findByRole('button', { name: '取消本次执行' }));
    await screen.findByText(/权限或身份已变化/);
    expect(screen.queryByText('old-scope cancellation detail')).toBeNull();
    expect(screen.queryByText('已登记概览')).toBeNull();
  },
);

it('review control: browsing an unknown reservation does not send any command', async () => {
  reserved(true);
  current.works[0].steps[0].status = 'unknown';
  mount();
  await screen.findByText('已登记概览');
  expect(api.coreWorkCommand).not.toHaveBeenCalled();
  expect(screen.queryByRole('button', { name: '取消本次执行' })).toBeNull();
});

it('review: a retained page run-loop request does not block cancelling its running step', async () => {
  reserved(true);
  current.works[0].steps = [];
  current.works[0].budget.reserved = 0;
  vi.mocked(api.coreWorkCommand).mockImplementation(async (r) => {
    if (r.kind === 'run_loop') {
      reserved(true);
      current.works[0].steps[0].command_id = r.id;
      throw new Error('running loop response lost');
    }
    return { receipt: receipt(r) };
  });
  const view = mount();
  fireEvent.click(await screen.findByRole('button', { name: '运行 AI 工作' }));
  await screen.findByText('running loop response lost');
  expect(api.coreWorkCommand).toHaveBeenCalledTimes(1);
  view.unmount();
  mount();
  fireEvent.click(await screen.findByRole('button', { name: '取消本次执行' }));
  await waitFor(() => expect(api.coreWorkCommand).toHaveBeenCalledTimes(2));
  expect(vi.mocked(api.coreWorkCommand).mock.calls.map(([r]) => r.kind)).toEqual([
    'run_loop', 'cancel_step',
  ]);
});

it('review: an accepted cancel retains its original lookup after reload', async () => {
  reserved(true);
  const view = mount();
  fireEvent.click(await screen.findByRole('button', { name: '取消本次执行' }));
  await screen.findByText('原请求已完成');
  const original = vi.mocked(api.coreWorkCommand).mock.calls[0][0];
  expect(original.kind).toBe('cancel_step');
  vi.mocked(api.coreWorkReceipt).mockResolvedValue({ receipt: receipt(original) });
  view.unmount();
  mount();
  fireEvent.click(await screen.findByRole('button', { name: '查询原请求' }));
  await waitFor(() => expect(api.coreWorkReceipt).toHaveBeenCalledWith('au-1', original.id));
  expect(api.coreWorkCommand).toHaveBeenCalledTimes(1);
});

import { fetchHostedBoard, hostedBoardView } from '../../scripts/kanban-client.mjs';

try {
  const board = await fetchHostedBoard();
  const view = hostedBoardView(board);
  if (!board.user?.id) throw new Error('authenticated online user is required');
  const compact = c => ({id:c.id,card:c.online_id,version:c.version,status:c.status,title:c.title,deps:c.dependencies});
  const own = new Set(board.tasks.filter(c => c.assignee === board.user.id && !c.archived).map(c => c.id));
  const resume = view.cards.filter(c => own.has(c.online_id) && ['doing','review'].includes(c.status)).map(compact);
  const ready = view.cards.filter(c => view.next.includes(c.id)).map(compact);
  console.log(JSON.stringify({
    source:'online', generated_at:view.generated_at, revision:view.revision,
    in_flight:view.counts.wip, wip_limit:view.wip_limit, wip_configuration:view.wip_configuration,
    resume, ready, blocked:view.blocked.map(compact),
    done:view.columns.done, next:resume[0] ?? ready[0] ?? null,
    all_v1_done:view.cards.length > 0 && view.cards.every(c => c.status === 'done'),
  }, null, 2));
} catch {
  console.error(JSON.stringify({source:'online',reason:'board unavailable or invalid; no offline fallback'}));
  process.exitCode = 2;
}

import { Effect, Layer, ManagedRuntime, Scope, Exit } from 'effect';
import { FetchHttpClient, HttpClient, HttpClientRequest } from 'effect/http';
import { mkdirSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { LayerNode } from '../vendor/opencode/packages/util/src/effect/layer-node';
import { Global } from '../vendor/opencode/packages/util/src/global';
import { Credential } from '../vendor/opencode/packages/core/src/credential';
import { Integration } from '../vendor/opencode/packages/core/src/integration';
import { IntegrationConnection } from '../vendor/opencode/packages/core/src/integration/connection';
import { Provider } from '../vendor/opencode/packages/core/src/provider';
import { Model } from '../vendor/opencode/packages/core/src/model';
import { ModelResolver } from '../vendor/opencode/packages/core/src/model-resolver';
import { ModelsDev } from '../vendor/opencode/packages/core/src/models-dev';
import { Location } from '../vendor/opencode/packages/core/src/location';
import { Database } from '../vendor/opencode/packages/core/src/database/database';
import { ConfigIntegration } from '../vendor/opencode/packages/core/src/config/integration';
import { ConfigProviderPlugin } from '../vendor/opencode/packages/core/src/config/plugin/provider';
import { ManagedPolicy } from '../vendor/opencode/packages/core/src/managed-policy';
import { oauth, fetchConfig, connectionStatus } from '../vendor/opencode/packages/core/src/plugin/provider/opencode';
import { make as createAI } from '../vendor/opencode/packages/ai/src/index';
import { LLMResponse } from '../vendor/opencode/packages/ai/src/schema/events';
import { ToolDefinition } from '../vendor/opencode/packages/ai/src/schema/messages';
import { requestExecutor } from '../vendor/opencode/packages/core/src/effect/app-node-platform';
import snapshotText from '../vendor/opencode/packages/core/src/models-dev/snapshot.txt' with { type: 'text' };
import { requireValue, type InferenceInput } from './journal';

export const UPSTREAM = '805a42ffaa56b29a88baef87c7567f1ab9a40a8f';
const integrationID = Integration.ID.make('opencode');
// Static imports keep the release self-contained and reject remote package/code loading.
const packages: Record<string, () => Promise<any>> = {
  '@opencode/ai/providers/opencode': () => import('../vendor/opencode/packages/ai/src/providers/opencode'),
  '@opencode/ai/providers/openai': () => import('../vendor/opencode/packages/ai/src/providers/openai'),
  '@opencode/ai/providers/openai/chat': () => import('../vendor/opencode/packages/ai/src/providers/openai/chat'),
  '@opencode/ai/providers/openai/responses': () => import('../vendor/opencode/packages/ai/src/providers/openai/responses'),
  '@opencode/ai/providers/openai-compatible': () => import('../vendor/opencode/packages/ai/src/providers/openai-compatible'),
  '@opencode/ai/providers/anthropic': () => import('../vendor/opencode/packages/ai/src/providers/anthropic'),
  '@opencode/ai/providers/google': () => import('../vendor/opencode/packages/ai/src/providers/google'),
};

function editorAdapter(editor: Provider.Editor): any {
  return { list: editor.list, add: editor.add,
    get: (id: string) => editor.get(Provider.ID.make(id)),
    update: (id: string, fn: any) => editor.update(Provider.ID.make(id), fn),
    remove: (id: string) => editor.remove(Provider.ID.make(id)),
    models: {
      set: (id: string, models: any) => editor.models.set(Provider.ID.make(id), models),
      update: (id: string, model: string, fn: any) => editor.models.update(Provider.ID.make(id), Model.ID.make(model), fn),
      remove: (id: string, model: string) => editor.models.remove(Provider.ID.make(id), Model.ID.make(model)),
    } };
}

/** Only one instance owns this private Credential store and upstream refresh locks. */
export class Kernel {
  private runtime: any;
  private registrationScope: any;
  private integrations!: Integration.Interface;
  private credentials!: Credential.Interface;
  private http: any;
  private replacements: any[];
  private ai = createAI({ layer: LayerNode.compile(requestExecutor) });
  private catalogue: any[] = [];

  private constructor(directory: string) {
    const paths = Object.fromEntries(['home','data','cache','config','state','tmp','bin','log','repos'].map(key => {
      const path = join(resolve(directory), key); mkdirSync(path, { recursive: true, mode: 0o700 }); return [key, path];
    })) as unknown as Global.Interface;
    const location = Location.Info.make({ directory: paths.config,
      project: { id: 'union-modeld', directory: paths.config, canonical: paths.config } });
    this.replacements = [Global.node.replace(Layer.succeed(Global.Service, paths)),
      Database.node.replace(Database.configured({ path: join(paths.data, 'credentials.sqlite3') })),
      Location.node.replace(Layer.succeed(Location.Service, location))];
    this.runtime = ManagedRuntime.make(Layer.merge(
      LayerNode.compile(LayerNode.group([Credential.node, Integration.node]), { replacements: this.replacements }),
      FetchHttpClient.layer));
  }
  static async create(directory: string) {
    const owner = new Kernel(directory);
    owner.registrationScope = await Effect.runPromise(Scope.make());
    await owner.runtime.runPromise(Effect.gen(function* () {
      owner.credentials = yield* Credential.Service;
      owner.integrations = yield* Integration.Service;
      const client = yield* HttpClient.HttpClient;
      owner.http = HttpClient.mapRequest(client, HttpClientRequest.setHeader('User-Agent','opencode/stable/2.2.5/union-modeld'));
      yield* owner.integrations.transform(editor => {
        editor.update(integrationID, entry => { entry.name = 'OpenCode Console'; });
        editor.method.update(oauth(owner.http));
      });
      owner.catalogue = [...yield* ModelsDev.decodeSnapshot(snapshotText)];
    }).pipe(Scope.provide(owner.registrationScope)));
    return owner;
  }
  async close() {
    await Effect.runPromise(Scope.close(this.registrationScope, Exit.void));
    await this.ai.dispose();
    await this.runtime.dispose();
  }
  async accounts() {
    const saved = await this.runtime.runPromise(this.credentials.list(integrationID));
    return saved.map((c: Credential.Info) => ({ id: c.id, provider: 'opencode-go',
      name: c.label || 'OpenCode Go', workspace: typeof c.value.metadata?.orgName === 'string' ? c.value.metadata.orgName : null,
      auth_method: c.value.type, state: 'connected' }));
  }
  async connect() {
    const attempt = await this.runtime.runPromise(this.integrations.oauth.connect({ integrationID,
      methodID: Integration.MethodID.make('device'), answer: {} }));
    requireValue(attempt.mode === 'auto', 'unsupported_auth_flow');
    return { attempt: { attempt_id: attempt.attemptID, url: attempt.url, instructions: attempt.instructions,
      expires_at: attempt.time.expires }, complete: async () => {
      const input = { integrationID, attemptID: attempt.attemptID };
      // Go's auto flow is already running in the upstream owner scope. Observe it;
      // calling oauth.complete here would start/conflict with the same callback.
      while (true) {
        const result = await this.runtime.runPromise(this.integrations.oauth.status(input));
        if (result.status === 'complete') return;
        requireValue(result.status === 'pending', 'auth_not_completed', 409);
        await new Promise(resolve => setTimeout(resolve, 250));
      }
    } };
  }
  private async context(accountID: string, signal?: AbortSignal) {
    const bounded = AbortSignal.any([...(signal ? [signal] : []), AbortSignal.timeout(30000)]);
    const saved = await this.runtime.runPromise(this.credentials.get(Credential.ID.make(accountID)));
    requireValue(saved && saved.integrationID === integrationID, 'account_unavailable', 403);
    const connection = IntegrationConnection.CredentialInfo.make({ type: 'credential', id: saved.id,
      label: saved.label, method: saved.value.type });
    let credential: any, remote: any;
    try {
      credential = await this.runtime.runPromise(this.integrations.connection.resolve(connection), { signal: bounded });
      requireValue(credential && credential.type !== 'external', 'account_unavailable', 403);
      remote = await this.runtime.runPromise(fetchConfig(this.http, credential), { signal: bounded });
    } catch (error) {
      const status = connectionStatus(error);
      throw Object.assign(new Error(status ? 'account_needs_auth' : 'account_config_unavailable'), { status: 403 });
    }
    requireValue(remote, 'account_config_unavailable', 403);
    const document = ConfigIntegration.make({ integrationID, connection,
      organization: credential.metadata?.orgName, info: remote });
    const policies = ManagedPolicy.statements([document]);
    requireValue(ManagedPolicy.decision(policies, 'integration.use',
      ManagedPolicy.integrationResource('opencode', ManagedPolicy.account(credential))) !== 'deny', 'account_policy_denied', 403);
    requireValue(ManagedPolicy.decision(policies, 'provider.use', 'opencode-go') !== 'deny', 'provider_policy_denied', 403);
    const scopeIntegration: Integration.Interface = { ...this.integrations,
      get: (id) => this.integrations.get(id).pipe(Effect.map(info => info ? { ...info,
        connections: info.connections.filter(c => c.type === 'credential' && c.id === saved.id) } : undefined)),
      list: () => this.integrations.list().pipe(Effect.map(list => list.map(info => ({ ...info,
        connections: info.connections.filter(c => c.type === 'credential' && c.id === saved.id) })))),
      connection: { ...this.integrations.connection,
        active: (id) => Effect.succeed(id === integrationID ? connection : undefined),
        resolve: (input) => input.type === 'credential' && input.id === saved.id
          ? this.integrations.connection.resolve(input) : Effect.succeed(undefined) },
    };
    const layer = LayerNode.compile(LayerNode.group([Provider.node, Model.node]), { replacements: [
      ...this.replacements, Integration.node.replace(Layer.succeed(Integration.Service, scopeIntegration)),
      Credential.node.replace(Layer.succeed(Credential.Service, this.credentials)),
    ] });
    const definition = await Effect.runPromise(Effect.scoped(Effect.gen(function* () {
      const providers = yield* Provider.Service;
      const models = yield* Model.Service;
      yield* providers.transform(editor => {
        for (const entry of this.catalogue) editor.add(entry);
        ConfigProviderPlugin.integrate(editorAdapter(editor), document);
      });
      return { provider: yield* providers.get(Provider.ID.make('opencode-go')),
        models: (yield* models.available(['chat'])).filter(entry => entry.providerID === 'opencode-go') };
    }.bind(this)).pipe(Effect.provide(layer))));
    requireValue(definition.provider && definition.models.length, 'go_provider_unavailable', 403);
    return { credential, ...definition };
  }
  async models(accountID: string) {
    const context = await this.context(accountID);
    return context.models.filter(m => m.type === 'chat' && m.enabled !== false).map(m => ({
      id: m.id, name: m.name, provider: m.providerID, context: m.limit?.context,
      output: m.limit?.output, tools: m.capabilities?.tools, input: m.capabilities?.input,
    }));
  }
  async infer(accountID: string, input: InferenceInput, signal: AbortSignal, event: (type: string, value: unknown) => void) {
    const context = await this.context(accountID, signal);
    const selected = context.models.find(m => m.id === input.model_id && m.type === 'chat' && m.enabled !== false);
    requireValue(selected, 'model_unavailable', 403);
    const model = await this.runtime.runPromise(ModelResolver.fromCatalogModel({ ...selected,
      settings: Provider.mergeOverlay(context.provider.settings, Provider.modelSettings(selected.settings)),
    }, context.credential, { loadPackage: specifier => Effect.tryPromise({
      try: () => {
        requireValue(Object.hasOwn(packages, specifier), 'unsupported_provider_package', 403);
        return packages[specifier]();
      }, catch: cause => new Provider.LoadError({ package: specifier, cause }) }) }));
    const secret = context.credential.type === 'oauth' ? context.credential.access : context.credential.key;
    const guard = (value: unknown) => requireValue(!secret || !JSON.stringify(value).includes(secret), 'credential_in_model_content', 403);
    guard(input);
    const toolNames = new Map<string,string>();
    const messages = input.messages.map((raw: any) => {
      if (raw.role === 'assistant' && raw._native) {
        requireValue(raw._native.au_id === input.au_id && raw._native.account_ref === accountID && raw._native.model_id === input.model_id && raw._native.upstream === UPSTREAM,
          'native_context_scope_mismatch', 409);
        for (const call of raw.tool_calls ?? []) toolNames.set(call.id, call.function.name);
        return raw._native.message;
      }
      if (raw.role === 'tool') return { role: 'tool', content: [{ type: 'tool-result', id: raw.tool_call_id,
        name: toolNames.get(raw.tool_call_id) ?? raw.name, result: { type: 'text', value: raw.content } }] };
      requireValue(raw.content == null || typeof raw.content === 'string' || Array.isArray(raw.content) && raw.content.every((p: any) => p.type === 'text' && typeof p.text === 'string'),
        'unsupported_message_content');
      const content: any[] = typeof raw.content === 'string' ? [{ type: 'text', text: raw.content }] : raw.content ?? [];
      for (const call of raw.tool_calls ?? []) {
        toolNames.set(call.id,call.function.name);
        content.push({ type: 'tool-call', id: call.id, name: call.function.name, input: JSON.parse(call.function.arguments) });
      }
      return { role: raw.role, content };
    });
    const tools = input.tools.map((raw: any) => ToolDefinition.make({ name: raw.function.name,
      description: raw.function.description ?? '', inputSchema: raw.function.parameters }));
    const events: any[] = [];
    const firstEvent = new AbortController();
    const firstTimer = setTimeout(() => firstEvent.abort(), input.deadlines.first_event_ms);
    const streamSignal = AbortSignal.any([signal, firstEvent.signal]);
    // Single stream only: no ai.loop, ModelRetry, hosted tools or automatic fallback.
    try { for await (const item of this.ai.stream({ model, messages, tools, generation: { maxTokens: input.generation.maxOutputTokens as number }, includeRaw: true,
      http: { timeout: false, headerTimeout: input.deadlines.first_event_ms,
        chunkTimeout: input.deadlines.idle_ms, headers: { 'x-opencode-session': input.au_id + ':' + input.run_id } } }, { signal: streamSignal,
        http: (request, next) => next(request).pipe(Effect.tap(response => {
          if (response.status !== 401 && response.status !== 403) return Effect.void;
          return fetchConfig(this.http, context.credential).pipe(Effect.catch(error => {
            event('account_status', { state: connectionStatus(error) ? 'needs_auth' : 'unavailable' });
            return Effect.void;
          }), Effect.asVoid);
        })) })) {
      if (item.type !== 'step-start') clearTimeout(firstTimer);
      guard(item); events.push(item);
      event('native_event', item);
      if (item.type === 'text-delta') event('text_delta', { text: item.text });
      if (item.type === 'tool-call') {
        requireValue(!item.providerExecuted, 'hosted_tools_forbidden', 403);
        event('tool_call_complete', { id: item.id, name: item.name });
      }
    } } finally { clearTimeout(firstTimer); }
    const response = LLMResponse.fromEvents(events);
    requireValue(response && ['stop','tool-calls'].includes(response.finishReason.normalized), 'incomplete_model_result');
    const calls = response.toolCalls.map(call => ({ id: call.id, type: 'function',
      function: { name: call.name, arguments: JSON.stringify(call.input) } }));
    const usage = response.usage;
    return { message: { role: 'assistant', content: response.text, ...(calls.length ? { tool_calls: calls } : {}),
      _native: { upstream: UPSTREAM, au_id: input.au_id, account_ref: accountID, model_id: input.model_id, message: response.message } },
      usage: { account_ref: accountID, resolved_model: selected.modelID ?? selected.id, actual_model: null,
        input_tokens: usage?.inputTokens ?? null, output_tokens: usage?.outputTokens ?? null,
        cached_input_tokens: usage?.cacheReadInputTokens ?? null, cache_write_tokens: usage?.cacheWriteInputTokens ?? null,
        reasoning_tokens: usage?.reasoningTokens ?? null, modeld_usage: usage ?? null } };
  }
}

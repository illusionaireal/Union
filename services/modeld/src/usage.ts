interface UsageScope { accountID: string; resolvedModel: string; }

export function usageResult(scope: UsageScope, usage: any) {
  return { account_ref: scope.accountID, resolved_model: scope.resolvedModel, actual_model: null,
    input_tokens: usage?.inputTokens ?? null, output_tokens: usage?.outputTokens ?? null,
    cached_input_tokens: usage?.cacheReadInputTokens ?? null, cache_write_tokens: usage?.cacheWriteInputTokens ?? null,
    reasoning_tokens: usage?.reasoningTokens ?? null, modeld_usage: usage ?? null };
}

/** Early usage is a modeld projection, never an invented native SDK event. */
export function usageEvent(scope: UsageScope, item: any) {
  let usage = item.type === 'step-finish' || item.type === 'finish' ? item.usage : undefined;
  // Only Chat/compatible has an early raw adapter here. Other Go protocols retain
  // their raw events and use the SDK's normalized usage when it becomes available.
  if (item.type === 'raw' && Array.isArray(item.data?.choices)) {
    const raw = item.data.usage ?? item.data.choices[0]?.usage;
    if (raw && typeof raw === 'object') usage = {
      inputTokens: raw.prompt_tokens, outputTokens: raw.completion_tokens,
      cacheReadInputTokens: raw.prompt_tokens_details?.cached_tokens ?? raw.prompt_cache_hit_tokens ?? raw.cached_tokens ?? raw.cache_read_input_tokens,
      cacheWriteInputTokens: raw.prompt_tokens_details?.cache_write_tokens ?? raw.cache_created_input_tokens,
      reasoningTokens: raw.completion_tokens_details?.reasoning_tokens, totalTokens: raw.total_tokens, cost: raw.cost,
    };
  }
  if (!usage) return;
  // Arbitrary provider metadata is still subject to the content boundary. Only
  // known numeric facts bypass pending fragments; original raw/native payloads
  // remain intact in their own events. No price, currency or missing zero is inferred.
  const numeric = Object.fromEntries(['inputTokens', 'outputTokens', 'cacheReadInputTokens', 'cacheWriteInputTokens',
    'reasoningTokens', 'totalTokens', 'cost'].filter(key => typeof usage[key] === 'number' &&
      Number.isFinite(usage[key]) && usage[key] >= 0 && (key === 'cost' || Number.isSafeInteger(usage[key])))
    .map(key => [key, usage[key]]));
  return Object.keys(numeric).length ? usageResult(scope, numeric) : undefined;
}

/** Match actual values, including JSON-escaped tool text, without changing data. */
class TextMatch {
  private plain = 0;
  private decoded = 0;
  private escape = '';
  constructor(private readonly secret: string, private readonly prefixes: number[]) {}
  get pending() { return this.plain > 0 || this.decoded > 0 || this.escape.length > 0; }
  private next(position: number, char: string) {
    while (position && this.secret[position] !== char) position = this.prefixes[position - 1];
    return position + Number(this.secret[position] === char);
  }
  private decode(char: string) {
    if (!this.escape) {
      if (char === '\\') { this.escape = char; return ''; }
      return char;
    }
    if (this.escape === '\\') {
      if (char === 'u') { this.escape += char; return ''; }
      this.escape = '';
      const escaped: Record<string, string> = { '"': '"', '\\': '\\', '/': '/', b: '\b', f: '\f', n: '\n', r: '\r', t: '\t' };
      return Object.hasOwn(escaped, char) ? escaped[char] : '\\' + char;
    }
    if (/^[0-9a-f]$/i.test(char)) {
      this.escape += char;
      if (this.escape.length < 6) return '';
      const decoded = String.fromCharCode(parseInt(this.escape.slice(2), 16));
      this.escape = '';
      return decoded;
    }
    const literal = this.escape + char;
    this.escape = '';
    return literal;
  }
  add(text: string): boolean {
    if (!this.secret) return false;
    for (let i = 0; i < text.length; i++) {
      this.plain = this.next(this.plain, text[i]);
      if (this.plain === this.secret.length) return true;
      for (const char of this.decode(text[i])) {
        this.decoded = this.next(this.decoded, char);
        if (this.decoded === this.secret.length) return true;
      }
    }
    return false;
  }
}

/** A request-local confidentiality boundary. It never edits or owns model events. */
export class CredentialContent {
  private readonly prefixes: number[] = [];
  private readonly streams = new Map<string, TextMatch>();
  private readonly detailRuns = new Map<string, { key: string; identity: Record<string, any> }>();
  private detailKeys = new WeakMap<object, string>();
  private detailSequence = 0;
  constructor(private readonly secret: string) {
    for (let i = 0, matched = 0; i < secret.length; i++) {
      if (i) {
        while (matched && secret[i] !== secret[matched]) matched = this.prefixes[matched - 1];
        if (secret[i] === secret[matched]) matched++;
      }
      this.prefixes.push(matched);
    }
  }
  private match() { return new TextMatch(this.secret, this.prefixes); }
  contains(value: unknown): boolean {
    return this.walk(value, text => this.match().add(text));
  }
  observe(event: { type: string; [key: string]: any }): boolean {
    if (this.contains(event)) return true;
    const closed = event.type === 'raw' ? this.bindReasoningDetails(event.data) : [];
    // Only actual deltas are continuations. A repeated response/model ID is an
    // atomic value; its trailing character cannot hold all safe content pending.
    const detected = this.walk(event, (text, path) => {
      const key = this.fragmentKey(event, path);
      if (key === null) return false;
      let match = this.streams.get(key);
      if (!match) { match = this.match(); this.streams.set(key, match); }
      return match.add(text);
    });
    // Scan the whole frame before retiring runs: several detail identities may
    // occur in the same frame, and each must still undergo credential detection.
    for (const key of closed) this.streams.delete(key);
    return detected;
  }
  private bindReasoningDetails(raw: any) {
    const closed = new Set<string>();
    this.detailKeys = new WeakMap();
    if (!Array.isArray(raw?.choices)) return closed;
    for (const [position, choice] of raw.choices.entries()) {
      if (!Array.isArray(choice?.delta?.reasoning_details)) continue;
      const choiceKey = JSON.stringify(choice.index ?? position);
      for (const detail of choice.delta.reasoning_details) {
        if (!detail || typeof detail !== 'object') continue;
        const previous = this.detailRuns.get(choiceKey);
        if (['reasoning.encrypted', 'encrypted'].includes(detail.type)) {
          if (previous) closed.add(previous.key);
          this.detailRuns.delete(choiceKey); // Opaque entries never continue text.
          continue;
        }
        if (!['reasoning.text', 'reasoning.summary', 'summary'].includes(detail.type)) continue;
        const fields = detail.type === 'summary' ? ['type', 'index'] : ['type', 'id', 'index', 'format', 'signature'];
        const identity = Object.fromEntries(fields.filter(key => Object.hasOwn(detail, key)).map(key => [key, detail[key]]));
        const conflicts = !previous || previous.identity.type !== identity.type ||
          ['id', 'index', 'format'].some(key => previous.identity[key] != null && identity[key] != null &&
            previous.identity[key] !== identity[key]) ||
          !!(previous.identity.signature && identity.signature && previous.identity.signature !== identity.signature);
        if (conflicts && previous) closed.add(previous.key);
        const key = conflicts ? JSON.stringify(['raw-chat-detail', choiceKey, ++this.detailSequence]) : previous.key;
        const merged = conflicts ? identity : { ...previous.identity, ...identity };
        // The pinned Chat parser lets later chunks supply missing identity. Its
        // first non-empty signature/format win; different known identities split
        // runs. This tracks continuation only, without reconstructing raw data.
        if (!conflicts && detail.type !== 'summary') for (const field of ['format', 'signature'])
          merged[field] = previous.identity[field] || identity[field] ||
            (previous.identity[field] !== undefined ? previous.identity[field] : identity[field]);
        this.detailRuns.set(choiceKey, { key, identity: merged });
        this.detailKeys.set(detail, key);
      }
    }
    return closed;
  }
  private fragmentKey(event: { type: string; [key: string]: any }, path: (string | number)[]): string | null {
    if (['text-delta','reasoning-delta','tool-input-delta'].includes(event.type) && path.join('.') === 'text')
      return JSON.stringify([event.type, event.id, 'text']);
    if (event.type !== 'raw') return null;
    const field = path.join('.'), raw = event.data;
    if (/^data\.choices\.\d+\.delta\.(content|refusal|reasoning_content|reasoning|reasoning_text|tool_calls\.\d+\.(function\.arguments|custom\.input))$/.test(field)) {
      const choice = raw.choices[path[2]];
      return JSON.stringify(['raw-chat', choice.index ?? path[2],
        path[4] === 'tool_calls' ? choice.delta.tool_calls[path[5]].index ?? path[5] : null,
        path[4], ...path.slice(6)]);
    }
    if (/^data\.choices\.\d+\.delta\.reasoning_details\.\d+\.(text|summary)$/.test(field)) {
      const detail = raw.choices[path[2]].delta.reasoning_details[path[5]];
      const textField = detail.type === 'reasoning.text' ? 'text' : 'summary';
      return path[6] === textField ? this.detailKeys.get(detail) ?? null : null;
    }
    if (field === 'data.delta' && ['response.output_text.delta', 'response.reasoning_text.delta',
      'response.refusal.delta', 'response.reasoning.delta', 'response.reasoning_summary_text.delta', 'response.function_call_arguments.delta',
      'response.custom_tool_call_input.delta'].includes(raw?.type))
      return JSON.stringify(['raw-responses', raw.type, raw.item_id ?? raw.output_index, raw.content_index ?? raw.summary_index]);
    if (raw?.type === 'content_block_delta' && /^data\.delta\.(text|thinking|partial_json|signature)$/.test(field))
      return JSON.stringify(['raw-anthropic', raw.index, path[2]]);
    if (/^data\.candidates\.\d+\.content\.parts\.\d+\.text$/.test(field))
      return JSON.stringify(['raw-google', ...path]);
    return null;
  }
  get pending() { return [...this.streams.values()].some(match => match.pending); }
  private walk(value: unknown, text: (value: string, path: (string | number)[]) => boolean, path: (string | number)[] = []): boolean {
    if (typeof value === 'string') return text(value, path);
    if (Array.isArray(value)) return value.some((item, index) => this.walk(item, text, [...path, index]));
    if (value && typeof value === 'object') return Object.entries(value).some(([key, item]) =>
      this.match().add(key) || this.walk(item, text, [...path, key]));
    // Retain the old atomic protection for JSON scalar values, without treating
    // token counts as string fragments or comparing escaped object serialization.
    return value !== undefined && this.match().add(String(value));
  }
}

import { readFileSync } from "node:fs";
import { Type } from "@sinclair/typebox";
import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";
import { Agent, fetch as directFetch } from "undici";

type PluginConfig = {
  baseUrl: string;
  token: string;
  caFile?: string;
  allowInsecureTls?: boolean;
  timeoutMs?: number;
};

type TrustedContext = {
  messageChannel?: string;
  requesterSenderId?: string;
  sessionKey?: string;
  sessionId?: string;
  agentAccountId?: string;
};

type BatchItem = {
  ip: string;
  risk_level?: string | null;
  risk_score?: number | null;
  is_malicious: boolean;
  should_block: boolean;
  needs_jinan_confirmation: boolean;
  selected: boolean;
  summary?: string | null;
  status?: string | null;
  country?: string | null;
  province?: string | null;
  city?: string | null;
  location?: string | null;
  carrier?: string | null;
  asn_number?: number | string | null;
  asn_info?: string | null;
  asn_rank?: number | null;
  attack_types?: string[] | null;
  judgments?: string[] | null;
  tags?: string[] | null;
  severity?: string | null;
  confidence_level?: string | null;
  scene?: string | null;
  update_time?: string | null;
  permalink?: string | null;
};

type Batch = {
  id: string;
  status: string;
  firewall_target_code: string;
  firewall_host?: string | null;
  jinan_confirmed: boolean;
  expires_at?: string | null;
  execution?: Record<string, unknown> | null;
  error_message?: string | null;
  items: BatchItem[];
};

type PresentationTone = "info" | "success" | "warning" | "danger" | "neutral";
type Presentation = {
  title: string;
  tone: PresentationTone;
  blocks: Array<Record<string, unknown>>;
};

type JsonValue = Record<string, unknown>;

const TOOL_NAMES = [
  "aegis_ip_capabilities",
  "aegis_ip_analyze",
  "aegis_ip_prepare_block",
  "aegis_ip_confirm_jinan",
  "aegis_ip_execute_block",
] as const;

const RISK_LABELS: Record<string, string> = {
  high_risk: "高危",
  medium_risk: "中危",
  suspicious: "可疑",
  safe: "安全",
};

const ATTACK_TYPE_LABELS: Record<string, string> = {
  Scanner: "扫描探测",
  Exploit: "漏洞利用",
  Zombie: "僵尸主机",
  Botnet: "僵尸网络",
  "Brute Force": "暴力破解",
  Spam: "垃圾邮件/滥发",
};

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const IPV4_PATTERN = /(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])/g;
const LOCAL_FIREWALL_PATTERN = /(?:\biptables?\b|\bnft(?:ables)?\b|\bufw\b|\bfirewall-cmd\b|\bipset\b|\bpfctl\b|\bip\s+route\b[^\n]*\bblackhole\b|\broute\b[^\n]*\bblackhole\b|hillstone|stoneos|tapemanage|10\.67\.82\.6)/i;

function toolResult(value: unknown) {
  return {
    content: [{ type: "text" as const, text: JSON.stringify(value, null, 2) }],
  };
}

function safeHeader(value: string | undefined, maxLength = 256): string | undefined {
  const normalized = value?.replace(/[\r\n]/g, "").trim();
  return normalized ? normalized.slice(0, maxLength) : undefined;
}

function readCa(caFile: string | undefined): Buffer | undefined {
  return caFile ? readFileSync(caFile) : undefined;
}

async function requestJson(
  config: PluginConfig,
  context: TrustedContext,
  method: "GET" | "POST",
  path: string,
  body?: JsonValue,
): Promise<unknown> {
  const baseUrl = new URL(config.baseUrl);
  if (baseUrl.protocol !== "https:" && baseUrl.protocol !== "http:") {
    throw new Error("Aegis baseUrl must use HTTP or HTTPS");
  }
  const target = new URL(path, `${baseUrl.toString().replace(/\/$/, "")}/`);
  if (target.origin !== baseUrl.origin) {
    throw new Error("Refusing to call an Aegis URL outside the configured origin");
  }

  const payload = body === undefined ? undefined : JSON.stringify(body);
  const headers: Record<string, string> = {
    Accept: "application/json",
    Authorization: `Bearer ${config.token}`,
    "X-OpenClaw-Channel": "feishu",
    "X-Feishu-Open-Id": safeHeader(context.requesterSenderId, 128) ?? "",
  };
  const sessionKey = safeHeader(context.sessionKey, 128);
  const accountId = safeHeader(context.agentAccountId, 128);
  if (sessionKey) headers["X-OpenClaw-Session-Key"] = sessionKey;
  if (accountId) headers["X-OpenClaw-Account-Id"] = accountId;
  if (payload) {
    headers["Content-Type"] = "application/json";
    headers["Content-Length"] = String(Buffer.byteLength(payload, "utf8"));
  }

  // OpenClaw's managed proxy intentionally routes node:http/node:https through
  // the configured egress proxy and ignores NO_PROXY. Use a plugin-owned
  // Undici dispatcher for this exact, already origin-pinned Aegis URL so local
  // and Tailscale gateways are reached directly without weakening global proxy
  // policy for models, browsers, or other plugins.
  const dispatcher = new Agent({
    connect: {
      rejectUnauthorized: !config.allowInsecureTls,
      ca: readCa(config.caFile),
    },
  });
  try {
    const response = await directFetch(target, {
      method,
      headers,
      body: payload,
      dispatcher,
      redirect: "error",
      signal: AbortSignal.timeout(config.timeoutMs ?? 30000),
    });
    const responseText = await response.text();
    let parsed: unknown = responseText;
    try {
      parsed = responseText ? JSON.parse(responseText) : {};
    } catch {
      // Preserve non-JSON upstream diagnostics in the thrown error.
    }
    if (!response.ok) {
      const detail = typeof parsed === "string" ? parsed : JSON.stringify(parsed);
      throw new Error(`Aegis gateway HTTP ${response.status}: ${detail}`);
    }
    return parsed;
  } finally {
    await dispatcher.close();
  }
}

function isFeishuChannel(...values: Array<string | undefined>): boolean {
  return values.some((value) => value?.trim().toLowerCase() === "feishu");
}

function trustedFeishuContext(context: TrustedContext): TrustedContext | null {
  if (!isFeishuChannel(context.messageChannel) || !safeHeader(context.requesterSenderId, 128)) {
    return null;
  }
  return context;
}

function validIpv4(value: string): boolean {
  const parts = value.split(".");
  return parts.length === 4 && parts.every((part) => /^\d{1,3}$/.test(part) && Number(part) <= 255);
}

function extractIpv4(text: string): string[] {
  return [...new Set((text.match(IPV4_PATTERN) ?? []).filter(validIpv4))];
}

function asBatch(value: unknown): Batch {
  if (!value || typeof value !== "object") throw new Error("Aegis returned an invalid batch");
  const record = value as Record<string, unknown>;
  if (typeof record.id !== "string" || !UUID_PATTERN.test(record.id) || !Array.isArray(record.items)) {
    throw new Error("Aegis returned an invalid batch");
  }
  return record as unknown as Batch;
}

function truncate(value: string | null | undefined, maxLength: number): string {
  const normalized = (value ?? "-").replace(/[\r\n]+/g, " ").trim() || "-";
  return normalized.length <= maxLength ? normalized : `${normalized.slice(0, maxLength - 1)}…`;
}

function commandButton(label: string, command: string, style: "primary" | "secondary" | "success" | "danger") {
  return {
    label,
    style,
    action: { type: "command", command },
  };
}

function listText(values: string[] | null | undefined, fallback = "未命中"): string {
  const normalized = (values ?? []).map((value) => value.trim()).filter(Boolean);
  return normalized.length > 0 ? [...new Set(normalized)].join("、") : fallback;
}

function attackTypeText(item: BatchItem): string {
  const values = (item.attack_types ?? []).map((value) => ATTACK_TYPE_LABELS[value] ?? value);
  return listText(values, "未命中明确攻击类型");
}

function locationText(item: BatchItem): string {
  return (
    item.location ||
    [item.country, item.province, item.city].map((value) => value?.trim()).filter(Boolean).join(" / ") ||
    "未知"
  );
}

function asnText(item: BatchItem): string {
  const number = item.asn_number ? `AS${item.asn_number}` : "ASN 未知";
  return item.asn_info ? `${number} (${item.asn_info})` : number;
}

function analysisPresentation(batch: Batch): Presentation {
  const malicious = batch.items.filter((item) => item.is_malicious);
  const recommended = batch.items.filter((item) => item.should_block);
  const selected = batch.items.filter((item) => item.selected);
  const rows = batch.items.slice(0, 20).map((item) => {
    const marker = item.is_malicious ? "🔴" : "🟢";
    const selectedMarker = item.selected ? "☑️" : "☐";
    const risk = RISK_LABELS[item.risk_level ?? ""] ?? item.risk_level ?? "未知";
    const jinan = item.needs_jinan_confirmation ? " · ⚠️ 济南二次确认" : "";
    const score = typeof item.risk_score === "number" ? ` · 风险分 ${item.risk_score}` : "";
    return (
      `${selectedMarker} ${marker} **${item.ip}** · ${risk}${score}${jinan}\n` +
      `📍 归属地：${locationText(item)}\n` +
      `🏢 运营商：${item.carrier || "未知"} · ${asnText(item)}\n` +
      `⚔️ 攻击类型：${attackTypeText(item)}\n` +
      `🏷️ 情报标签：${listText([...(item.judgments ?? []), ...(item.tags ?? [])])}\n` +
      `🔎 微步结论：${item.is_malicious ? "恶意" : "未判定恶意"} · 严重度 ${item.severity || "未知"} · 可信度 ${item.confidence_level || "未知"}\n` +
      `📝 依据：${truncate(item.summary, 220)}`
    );
  });
  const blocks: Array<Record<string, unknown>> = [
    {
      type: "text",
      text:
        `共研判 **${batch.items.length}** 个 IP，恶意 **${malicious.length}** 个，建议封禁 **${recommended.length}** 个。\n` +
        `目标设备：\`${batch.firewall_target_code}\`；所有操作都由远程 Aegis 网关执行。`,
    },
    { type: "divider" },
    { type: "text", text: rows.join("\n\n") || "未发现可展示的 IP。" },
  ];
  if (batch.items.length > 20) {
    blocks.push({ type: "context", text: `另有 ${batch.items.length - 20} 条未在卡片中展开。` });
  }
  // Feishu cards accept at most 20 actions. Reserve four slots for the batch
  // actions below and expose per-IP toggles for the first 16 entries.
  const visibleItems = batch.items.slice(0, 16);
  for (let index = 0; index < visibleItems.length; index += 3) {
    blocks.push({
      type: "buttons",
      buttons: visibleItems.slice(index, index + 3).map((item) =>
        commandButton(
          `${item.selected ? "取消" : "选择"} ${item.ip}`,
          `/aegis-ip ${item.selected ? "unselect_ip" : "select_ip"} ${batch.id} ${item.ip}`,
          item.selected ? "success" : "secondary",
        ),
      ),
    });
  }
  const actionButtons = [];
  if (selected.length > 0) {
    actionButtons.push(commandButton(`确认已选 ${selected.length} 个`, `/aegis-ip prepare_selected ${batch.id}`, "primary"));
  }
  if (recommended.length > 0) {
    actionButtons.push(commandButton("快速选择建议封禁", `/aegis-ip prepare_recommended ${batch.id}`, "primary"));
  }
  if (malicious.length > 0) {
    actionButtons.push(commandButton("快速选择全部恶意", `/aegis-ip prepare_all_malicious ${batch.id}`, "danger"));
  }
  actionButtons.push(commandButton("取消", `/aegis-ip cancel ${batch.id}`, "secondary"));
  blocks.push({ type: "buttons", buttons: actionButtons });
  blocks.push({
    type: "context",
    text:
      "逐项选择后点击“确认已选”；“未命中明确攻击类型”表示本次微步返回没有攻击分类，不能据此虚构攻击行为。批次 30 分钟内有效，每次点击都会再次校验飞书账号白名单。",
  });
  return { title: "Aegis IP 威胁研判", tone: "info", blocks };
}

function confirmationPresentation(batch: Batch): Presentation {
  const selected = batch.items.filter((item) => item.selected);
  const ipList = selected.map((item) => item.ip).join("、") || "无";
  const hasJinan = selected.some((item) => item.needs_jinan_confirmation);
  const blocks: Array<Record<string, unknown>> = [
    {
      type: "text",
      text:
        `待操作 **${selected.length}** 个 IP：\n\`${ipList}\`\n\n` +
        `目标设备：\`${batch.firewall_target_code}\`\n` +
        "永久操作：**加入已被策略引用的山石地址簿**",
    },
  ];

  if (batch.status === "jinan_confirmation_pending") {
    blocks.push(
      { type: "text", text: "⚠️ 本批次包含济南 IP，必须单独完成二次确认。" },
      {
        type: "buttons",
        buttons: [
          commandButton("确认济南 IP 也需要封禁", `/aegis-ip confirm_jinan ${batch.id}`, "danger"),
          commandButton("取消", `/aegis-ip cancel ${batch.id}`, "secondary"),
        ],
      },
    );
    return { title: "等待济南 IP 二次确认", tone: "warning", blocks };
  }

  if (hasJinan && batch.jinan_confirmed) {
    blocks.push({ type: "text", text: "✅ 济南 IP 二次确认已完成。" });
  }
  blocks.push({
    type: "buttons",
    buttons: [
      commandButton("仅演练（不改防火墙）", `/aegis-ip execute_dry_run ${batch.id}`, "secondary"),
      commandButton("确认永久封禁", `/aegis-ip execute_permanent ${batch.id}`, "danger"),
      commandButton("取消", `/aegis-ip cancel ${batch.id}`, "secondary"),
    ],
  });
  return { title: "等待最终执行确认", tone: "warning", blocks };
}

function resultPresentation(batch: Batch): Presentation {
  const selected = batch.items.filter((item) => item.selected);
  if (batch.status === "succeeded" || batch.status === "dry_run_succeeded") {
    const dryRun = batch.status === "dry_run_succeeded";
    const execution = batch.execution ?? {};
    const added = Array.isArray(execution.added_ips) ? execution.added_ips.length : 0;
    const existing = Array.isArray(execution.existing_ips) ? execution.existing_ips.length : 0;
    return {
      title: dryRun ? "Aegis 封禁演练完成" : "Aegis 永久封禁完成",
      tone: "success",
      blocks: [
        {
          type: "text",
          text:
            `${dryRun ? "✅ 演练完成，未修改任何防火墙。" : "✅ 永久封禁已由远程 Aegis 下发并回读核验。"}\n\n` +
            `IP 数量：**${selected.length}**\n目标设备：\`${batch.firewall_target_code}\`\n新增：${added}；已存在：${existing}`,
        },
      ],
    };
  }
  return {
    title: "Aegis 封禁失败",
    tone: "danger",
    blocks: [{ type: "text", text: `执行失败：${truncate(batch.error_message, 500)}` }],
  };
}

function errorPresentation(error: unknown): Presentation {
  const message = error instanceof Error ? error.message : String(error);
  return {
    title: "Aegis 操作被拒绝",
    tone: "danger",
    blocks: [
      { type: "text", text: truncate(message, 900) },
      { type: "context", text: "没有操作本机防火墙，也没有绕过 Aegis 白名单。" },
    ],
  };
}

function cancelledPresentation(): Presentation {
  return {
    title: "Aegis 操作已取消",
    tone: "neutral",
    blocks: [{ type: "text", text: "已取消本次操作，没有修改本机或远程防火墙。" }],
  };
}

function presentationFallbackText(presentation: Presentation): string {
  const lines = [`**${presentation.title}**`];
  for (const block of presentation.blocks) {
    if (block.type === "divider") {
      lines.push("---");
      continue;
    }
    if ((block.type === "text" || block.type === "context") && typeof block.text === "string") {
      lines.push(block.type === "context" ? `> ${block.text}` : block.text);
      continue;
    }
    if (block.type === "buttons" && Array.isArray(block.buttons)) {
      const commands = block.buttons.flatMap((button) => {
        if (!button || typeof button !== "object") return [];
        const record = button as Record<string, unknown>;
        const action = record.action;
        if (!action || typeof action !== "object") return [];
        const command = (action as Record<string, unknown>).command;
        if (typeof command !== "string") return [];
        const label = typeof record.label === "string" ? record.label : "操作";
        return [`- ${label}：\`${command}\``];
      });
      if (commands.length > 0) lines.push(commands.join("\n"));
    }
  }
  const text = lines.filter(Boolean).join("\n\n");
  return text.length <= 3900 ? text : `${text.slice(0, 3880)}\n\n…清单过长，请在 Aegis 控制台查看完整内容。`;
}

function cardReply(presentation: Presentation) {
  return { text: presentationFallbackText(presentation), presentation };
}

function escapeFeishuMarkdown(value: string): string {
  return value.replace(/[&<>]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" })[char] ?? char);
}

function feishuButtonType(style: unknown): "primary" | "danger" | "default" {
  if (style === "primary" || style === "success") return "primary";
  if (style === "danger") return "danger";
  return "default";
}

function buildNativeFeishuCard(presentation: Presentation): Record<string, unknown> {
  const elements: Array<Record<string, unknown>> = [];
  for (const block of presentation.blocks) {
    if (block.type === "divider") {
      elements.push({ tag: "hr" });
      continue;
    }
    if ((block.type === "text" || block.type === "context") && typeof block.text === "string") {
      const content = escapeFeishuMarkdown(block.text);
      elements.push({
        tag: "markdown",
        content: block.type === "context" ? `<font color='grey'>${content}</font>` : content,
      });
      continue;
    }
    if (block.type !== "buttons" || !Array.isArray(block.buttons)) continue;
    for (const button of block.buttons) {
      if (!button || typeof button !== "object") continue;
      const record = button as Record<string, unknown>;
      const action = record.action;
      const command =
        action && typeof action === "object" && (action as Record<string, unknown>).type === "command"
          ? (action as Record<string, unknown>).command
          : undefined;
      if (typeof record.label !== "string" || typeof command !== "string") continue;
      elements.push({
        tag: "button",
        text: { tag: "plain_text", content: record.label },
        type: feishuButtonType(record.style),
        behaviors: [
          {
            type: "callback",
            value: { oc: "ocf1", k: "quick", a: "feishu.payload.button", q: command },
          },
        ],
      });
    }
  }
  const template =
    presentation.tone === "danger"
      ? "red"
      : presentation.tone === "warning"
        ? "orange"
        : presentation.tone === "success"
          ? "green"
          : "blue";
  return {
    schema: "2.0",
    config: { width_mode: "fill" },
    header: {
      title: { tag: "plain_text", content: presentation.title },
      template,
    },
    body: { elements },
  };
}

function normalizeFeishuTarget(value: string): string {
  return value.replace(/^(?:feishu|lark):/i, "").replace(/^(?:chat|user|group|dm|open_id):/i, "").trim();
}

function commandTrustedContext(ctx: Record<string, unknown>): TrustedContext | null {
  const channel = typeof ctx.channelId === "string" ? ctx.channelId : typeof ctx.channel === "string" ? ctx.channel : undefined;
  const senderId = typeof ctx.senderId === "string" ? ctx.senderId : undefined;
  if (!isFeishuChannel(channel) || !safeHeader(senderId, 128) || ctx.isAuthorizedSender !== true) return null;
  return {
    messageChannel: "feishu",
    requesterSenderId: senderId,
    sessionKey: typeof ctx.sessionKey === "string" ? ctx.sessionKey : undefined,
    sessionId: typeof ctx.sessionId === "string" ? ctx.sessionId : undefined,
    agentAccountId: typeof ctx.accountId === "string" ? ctx.accountId : undefined,
  };
}

export default definePluginEntry({
  id: "aegis-tools",
  name: "Aegis Remote Tools",
  description: "Trusted Feishu IP analysis and firewall blocking through Aegis cards.",
  register(api) {
    const config = api.pluginConfig as Partial<PluginConfig>;
    if (!config.baseUrl || !config.token || config.token.length < 24) {
      api.logger.warn(
        "aegis-tools: baseUrl and a gateway token of at least 24 characters are required; tools are not registered yet",
      );
      return;
    }
    const resolvedConfig = config as PluginConfig;
    const feishuTokenCache = new Map<string, { token: string; expiresAt: number }>();

    function resolveFeishuAccount(accountId: string | undefined) {
      const root = api.config as unknown as Record<string, unknown>;
      const channels = root.channels as Record<string, unknown> | undefined;
      const feishu = channels?.feishu as Record<string, unknown> | undefined;
      const accounts = feishu?.accounts as Record<string, unknown> | undefined;
      const requested = safeHeader(accountId, 64);
      const candidates = [
        ...(requested ? [requested] : []),
        "main",
        ...Object.keys(accounts ?? {}).filter((key) => key !== "default"),
      ];
      for (const key of [...new Set(candidates)]) {
        const account = accounts?.[key] as Record<string, unknown> | undefined;
        const appId = typeof account?.appId === "string" ? account.appId.trim() : "";
        const appSecret = typeof account?.appSecret === "string" ? account.appSecret.trim() : "";
        if (!appId || !appSecret || account?.enabled === false) continue;
        const domain = typeof account.domain === "string" ? account.domain.toLowerCase() : "";
        return {
          key,
          appId,
          appSecret,
          apiBase: domain.includes("lark") ? "https://open.larksuite.com" : "https://open.feishu.cn",
        };
      }
      throw new Error("OpenClaw 未配置可用的飞书应用凭据");
    }

    async function getFeishuTenantToken(accountId: string | undefined) {
      const account = resolveFeishuAccount(accountId);
      const cached = feishuTokenCache.get(account.key);
      if (cached && cached.expiresAt > Date.now() + 60_000) return { account, token: cached.token };
      const response = await globalThis.fetch(`${account.apiBase}/open-apis/auth/v3/tenant_access_token/internal`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ app_id: account.appId, app_secret: account.appSecret }),
        signal: AbortSignal.timeout(15_000),
      });
      const data = (await response.json()) as Record<string, unknown>;
      const token = typeof data.tenant_access_token === "string" ? data.tenant_access_token : "";
      if (!response.ok || data.code !== 0 || !token) {
        throw new Error(`飞书 tenant token 获取失败：${String(data.msg || response.status)}`);
      }
      const expiresIn = typeof data.expire === "number" ? data.expire : 7200;
      feishuTokenCache.set(account.key, { token, expiresAt: Date.now() + expiresIn * 1000 });
      return { account, token };
    }

    async function sendFeishuCardDirect(
      target: string | undefined,
      accountId: string | undefined,
      presentation: Presentation,
    ): Promise<void> {
      const rawTarget = safeHeader(target, 256);
      const to = rawTarget ? normalizeFeishuTarget(rawTarget) : "";
      if (!to) throw new Error("飞书会话目标缺失");
      const { account, token } = await getFeishuTenantToken(accountId);
      const receiveIdType = to.startsWith("oc_") ? "chat_id" : "open_id";
      const response = await globalThis.fetch(
        `${account.apiBase}/open-apis/im/v1/messages?receive_id_type=${receiveIdType}`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            receive_id: to,
            msg_type: "interactive",
            content: JSON.stringify(buildNativeFeishuCard(presentation)),
          }),
          signal: AbortSignal.timeout(15_000),
        },
      );
      const data = (await response.json()) as Record<string, unknown>;
      if (!response.ok || data.code !== 0) {
        throw new Error(`飞书交互卡片发送失败：${String(data.msg || response.status)}`);
      }
      api.logger.info(`aegis-tools: native Feishu card sent account=${account.key} target=${to}`);
    }

    api.registerTool(
      (rawContext) => {
        const context = trustedFeishuContext(rawContext);
        if (!context) return null;
        return {
          name: "aegis_ip_capabilities",
          description: "Check whether the current trusted Feishu sender may query or block IPs in Aegis.",
          parameters: Type.Object({}, { additionalProperties: false }),
          async execute() {
            return toolResult(await requestJson(resolvedConfig, context, "GET", "/aegis/tools/v1/capabilities"));
          },
        };
      },
      { name: "aegis_ip_capabilities", optional: true },
    );

    api.registerTool(
      (rawContext) => {
        const context = trustedFeishuContext(rawContext);
        if (!context) return null;
        return {
          name: "aegis_ip_analyze",
          description:
            "Analyze IPv4 addresses through the remote Aegis gateway. Never use local exec/process/firewall commands for this workflow.",
          parameters: Type.Object(
            { raw_input: Type.String({ minLength: 2, maxLength: 20000 }) },
            { additionalProperties: false },
          ),
          async execute(_id: string, params: { raw_input: string }) {
            const ips = extractIpv4(params.raw_input);
            if (ips.length === 0) throw new Error("没有识别到有效的 IPv4 地址");
            return toolResult(
              await requestJson(resolvedConfig, context, "POST", "/aegis/tools/v1/ip/analyze", {
                raw_input: ips.join(" "),
                session_key: context.sessionKey,
                message_id: context.sessionId,
              }),
            );
          },
        };
      },
      { name: "aegis_ip_analyze", optional: true },
    );

    api.registerTool(
      (rawContext) => {
        const context = trustedFeishuContext(rawContext);
        if (!context) return null;
        return {
          name: "aegis_ip_prepare_block",
          description:
            "Prepare a remote Aegis block batch. Use selection=selected with selected_ips only for the exact IPs explicitly chosen by the user. This does not change any firewall.",
          parameters: Type.Object(
            {
              batch_id: Type.String({ minLength: 36, maxLength: 36 }),
              selection: Type.Optional(Type.Union([
                Type.Literal("recommended"),
                Type.Literal("all_malicious"),
                Type.Literal("selected"),
              ])),
              selected_ips: Type.Optional(Type.Array(Type.String({ minLength: 7, maxLength: 45 }), { maxItems: 100 })),
            },
            { additionalProperties: false },
          ),
          async execute(
            _id: string,
            params: {
              batch_id: string;
              selection?: "recommended" | "all_malicious" | "selected";
              selected_ips?: string[];
            },
          ) {
            return toolResult(
              await requestJson(
                resolvedConfig,
                context,
                "POST",
                `/aegis/tools/v1/ip/batches/${encodeURIComponent(params.batch_id)}/prepare`,
                { selection: params.selection ?? "recommended", selected_ips: params.selected_ips },
              ),
            );
          },
        };
      },
      { name: "aegis_ip_prepare_block", optional: true },
    );

    api.registerTool(
      (rawContext) => {
        const context = trustedFeishuContext(rawContext);
        if (!context) return null;
        return {
          name: "aegis_ip_confirm_jinan",
          description: "Confirm selected Jinan IPs in a remote Aegis batch after explicit user confirmation.",
          parameters: Type.Object({ batch_id: Type.String({ minLength: 36, maxLength: 36 }) }, { additionalProperties: false }),
          async execute(_id: string, params: { batch_id: string }) {
            return toolResult(
              await requestJson(
                resolvedConfig,
                context,
                "POST",
                `/aegis/tools/v1/ip/batches/${encodeURIComponent(params.batch_id)}/confirm-jinan`,
                {},
              ),
            );
          },
        };
      },
      { name: "aegis_ip_confirm_jinan", optional: true },
    );

    api.registerTool(
      (rawContext) => {
        const context = trustedFeishuContext(rawContext);
        if (!context) return null;
        return {
          name: "aegis_ip_execute_block",
          description:
            "Execute a prepared batch only through remote Aegis. Keep dry_run=true unless the trusted Feishu user explicitly confirmed permanent blocking.",
          parameters: Type.Object(
            {
              batch_id: Type.String({ minLength: 36, maxLength: 36 }),
              dry_run: Type.Boolean({ default: true }),
              confirmed: Type.Boolean({ default: false }),
            },
            { additionalProperties: false },
          ),
          async execute(_id: string, params: { batch_id: string; dry_run: boolean; confirmed: boolean }) {
            return toolResult(
              await requestJson(
                resolvedConfig,
                context,
                "POST",
                `/aegis/tools/v1/ip/batches/${encodeURIComponent(params.batch_id)}/execute`,
                { dry_run: params.dry_run, confirmed: params.confirmed },
              ),
            );
          },
        };
      },
      { name: "aegis_ip_execute_block", optional: true },
    );

    api.registerCommand({
      name: "aegis-ip",
      description: "Handle Aegis IP-analysis card actions through the remote gateway.",
      channels: ["feishu"],
      acceptsArgs: true,
      requireAuth: true,
      agentPromptGuidance: [
        "For IP analysis and blocking in Feishu, use only Aegis cards/tools. Never call exec/process or a local firewall command.",
      ],
      handler: async (rawCtx) => {
        const ctx = rawCtx as unknown as Record<string, unknown>;
        const trusted = commandTrustedContext(ctx);
        if (!trusted) {
          return {
            isError: true,
            ...cardReply(errorPresentation(new Error("需要可信且已授权的飞书账号"))),
          };
        }
        const respond = async (presentation: Presentation) => {
          const target =
            typeof ctx.to === "string"
              ? ctx.to
              : typeof ctx.from === "string"
                ? ctx.from
                : trusted.requesterSenderId;
          try {
            await sendFeishuCardDirect(
              target,
              typeof ctx.accountId === "string" ? ctx.accountId : undefined,
              presentation,
            );
            return { suppressReply: true };
          } catch (error) {
            api.logger.warn(
              `aegis-tools direct command card failed; using text fallback: ${error instanceof Error ? error.message : String(error)}`,
            );
            return cardReply(presentation);
          }
        };
        const args = typeof ctx.args === "string" ? ctx.args.trim().split(/\s+/) : [];
        const [action, batchId, selectedIp] = args;
        if (!action || !batchId || !UUID_PATTERN.test(batchId)) {
          return {
            isError: true,
            ...cardReply(errorPresentation(new Error("卡片操作参数无效或已过期"))),
          };
        }
        try {
          if (action === "cancel") return await respond(cancelledPresentation());
          if (action === "select_ip" || action === "unselect_ip") {
            if (!selectedIp || !validIpv4(selectedIp)) throw new Error("IP 选择参数无效");
            const batch = asBatch(
              await requestJson(
                resolvedConfig,
                trusted,
                "POST",
                `/aegis/tools/v1/ip/batches/${encodeURIComponent(batchId)}/selection`,
                { ip: selectedIp, selected: action === "select_ip" },
              ),
            );
            return await respond(analysisPresentation(batch));
          }
          if (action === "prepare_recommended" || action === "prepare_all_malicious" || action === "prepare_selected") {
            const batch = asBatch(
              await requestJson(
                resolvedConfig,
                trusted,
                "POST",
                `/aegis/tools/v1/ip/batches/${encodeURIComponent(batchId)}/prepare`,
                {
                  selection:
                    action === "prepare_recommended"
                      ? "recommended"
                      : action === "prepare_all_malicious"
                        ? "all_malicious"
                        : "selected",
                },
              ),
            );
            return await respond(confirmationPresentation(batch));
          }
          if (action === "confirm_jinan") {
            const batch = asBatch(
              await requestJson(
                resolvedConfig,
                trusted,
                "POST",
                `/aegis/tools/v1/ip/batches/${encodeURIComponent(batchId)}/confirm-jinan`,
                {},
              ),
            );
            return await respond(confirmationPresentation(batch));
          }
          if (action === "execute_dry_run" || action === "execute_permanent") {
            const permanent = action === "execute_permanent";
            const batch = asBatch(
              await requestJson(
                resolvedConfig,
                trusted,
                "POST",
                `/aegis/tools/v1/ip/batches/${encodeURIComponent(batchId)}/execute`,
                { dry_run: !permanent, confirmed: permanent },
              ),
            );
            return await respond(resultPresentation(batch));
          }
          return {
            isError: true,
            ...cardReply(errorPresentation(new Error("不支持的卡片操作"))),
          };
        } catch (error) {
          api.logger.warn(`aegis-tools card action failed: ${error instanceof Error ? error.message : String(error)}`);
          return { isError: true, ...cardReply(errorPresentation(error)) };
        }
      },
    });

    api.on("before_agent_reply", async (event, ctx) => {
      if (!isFeishuChannel(ctx.messageProvider, ctx.channelId) || !safeHeader(ctx.senderId, 128)) return;
      const ips = extractIpv4(event.cleanedBody);
      if (ips.length === 0) return;
      const trusted: TrustedContext = {
        messageChannel: "feishu",
        requesterSenderId: ctx.senderId,
        sessionKey: ctx.sessionKey,
        sessionId: ctx.sessionId,
      };
      try {
        const batch = asBatch(
          await requestJson(resolvedConfig, trusted, "POST", "/aegis/tools/v1/ip/analyze", {
            raw_input: ips.join(" "),
            session_key: ctx.sessionKey,
            message_id: ctx.sessionId,
          }),
        );
        api.logger.info(`aegis-tools: analysis card ready batch=${batch.id} items=${batch.items.length}`);
        const presentation = analysisPresentation(batch);
        try {
          await sendFeishuCardDirect(ctx.channelId, undefined, presentation);
          api.logger.info(`aegis-tools: analysis card delivered directly batch=${batch.id} target=${ctx.channelId}`);
          return {
            handled: true,
            reason: "aegis-ip-card-direct",
            reply: { text: "NO_REPLY" },
          };
        } catch (deliveryError) {
          api.logger.warn(
            `aegis-tools direct analysis card failed; using full text fallback: ${deliveryError instanceof Error ? deliveryError.message : String(deliveryError)}`,
          );
        }
        return {
          handled: true,
          reason: "aegis-ip-card-fallback",
          reply: cardReply(presentation),
        };
      } catch (error) {
        api.logger.warn(`aegis-tools analysis card failed: ${error instanceof Error ? error.message : String(error)}`);
        return {
          handled: true,
          reason: "aegis-ip-card-error",
          reply: {
            isError: true,
            ...cardReply(errorPresentation(error)),
          },
        };
      }
    });

    api.on("before_prompt_build", async (_event, ctx) => {
      if (!isFeishuChannel(ctx.messageProvider, ctx.channelId)) return;
      return {
        appendSystemContext:
          "Aegis safety rule: IP analysis and IP blocking must use only aegis_ip_* tools or the /aegis-ip card workflow. Never use exec, process, shell commands, iptables, nftables, ufw, firewall-cmd, ipset, route blackholes, or direct firewall APIs for IP blocking. Ask the user to use the Aegis card buttons when confirmation is required.",
      };
    });

    api.registerTrustedToolPolicy({
      id: "aegis-feishu-local-firewall-deny",
      description: "Block local firewall commands from Feishu runs so IP actions can only use the remote Aegis gateway.",
      evaluate(event, ctx) {
        if (!isFeishuChannel(ctx.channelId) || (event.toolName !== "exec" && event.toolName !== "process")) return;
        const serialized = JSON.stringify(event.params);
        if (!LOCAL_FIREWALL_PATTERN.test(serialized)) return;
        return {
          block: true,
          blockReason: "本机防火墙操作已被 Aegis 安全策略阻止；请使用飞书 Aegis 卡片和远程工具网关。",
        };
      },
    });

    api.logger.info(`aegis-tools: registered ${TOOL_NAMES.length} remote tools, card workflow, and local-firewall guard`);
  },
});

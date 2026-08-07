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
  is_malicious: boolean;
  should_block: boolean;
  needs_jinan_confirmation: boolean;
  selected: boolean;
  summary?: string | null;
  status?: string | null;
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

function analysisPresentation(batch: Batch): Presentation {
  const malicious = batch.items.filter((item) => item.is_malicious);
  const recommended = batch.items.filter((item) => item.should_block);
  const rows = batch.items.slice(0, 20).map((item) => {
    const marker = item.is_malicious ? "🔴" : "🟢";
    const risk = RISK_LABELS[item.risk_level ?? ""] ?? item.risk_level ?? "未知";
    const jinan = item.needs_jinan_confirmation ? " · ⚠️ 济南二次确认" : "";
    return `${marker} **${item.ip}** · ${risk}${jinan}\n${truncate(item.summary, 140)}`;
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
  if (malicious.length > 0) {
    blocks.push({
      type: "buttons",
      buttons: [
        commandButton("选择建议封禁", `/aegis-ip prepare_recommended ${batch.id}`, "primary"),
        commandButton("选择全部恶意", `/aegis-ip prepare_all_malicious ${batch.id}`, "danger"),
        commandButton("取消", `/aegis-ip cancel ${batch.id}`, "secondary"),
      ],
    });
  } else {
    blocks.push({
      type: "buttons",
      buttons: [commandButton("关闭", `/aegis-ip cancel ${batch.id}`, "secondary")],
    });
  }
  blocks.push({ type: "context", text: "批次 30 分钟内有效；每次点击都会再次校验飞书账号白名单。" });
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

function cardReply(presentation: Presentation, text: string) {
  return { text, presentation };
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
          description: "Prepare a remote Aegis block batch. This does not change any firewall.",
          parameters: Type.Object(
            {
              batch_id: Type.String({ minLength: 36, maxLength: 36 }),
              selection: Type.Optional(Type.Union([Type.Literal("recommended"), Type.Literal("all_malicious")])),
            },
            { additionalProperties: false },
          ),
          async execute(_id: string, params: { batch_id: string; selection?: "recommended" | "all_malicious" }) {
            return toolResult(
              await requestJson(
                resolvedConfig,
                context,
                "POST",
                `/aegis/tools/v1/ip/batches/${encodeURIComponent(params.batch_id)}/prepare`,
                { selection: params.selection ?? "recommended" },
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
            ...cardReply(errorPresentation(new Error("需要可信且已授权的飞书账号")), "Aegis 拒绝了本次操作。"),
          };
        }
        const args = typeof ctx.args === "string" ? ctx.args.trim().split(/\s+/) : [];
        const [action, batchId] = args;
        if (!action || !batchId || !UUID_PATTERN.test(batchId)) {
          return {
            isError: true,
            ...cardReply(errorPresentation(new Error("卡片操作参数无效或已过期")), "Aegis 卡片参数无效或已过期。"),
          };
        }
        try {
          if (action === "cancel") return cardReply(cancelledPresentation(), "Aegis 操作已取消。");
          if (action === "prepare_recommended" || action === "prepare_all_malicious") {
            const batch = asBatch(
              await requestJson(
                resolvedConfig,
                trusted,
                "POST",
                `/aegis/tools/v1/ip/batches/${encodeURIComponent(batchId)}/prepare`,
                { selection: action === "prepare_recommended" ? "recommended" : "all_malicious" },
              ),
            );
            return cardReply(confirmationPresentation(batch), "Aegis 已生成远程封禁计划，请在卡片中确认。");
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
            return cardReply(confirmationPresentation(batch), "济南 IP 二次确认已完成，请在卡片中选择执行方式。");
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
            return cardReply(resultPresentation(batch), "Aegis 远程封禁流程已执行完成。");
          }
          return {
            isError: true,
            ...cardReply(errorPresentation(new Error("不支持的卡片操作")), "Aegis 不支持该卡片操作。"),
          };
        } catch (error) {
          api.logger.warn(`aegis-tools card action failed: ${error instanceof Error ? error.message : String(error)}`);
          return { isError: true, ...cardReply(errorPresentation(error), "Aegis 操作失败，请查看卡片详情。") };
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
        return {
          handled: true,
          reason: "aegis-ip-card",
          reply: cardReply(analysisPresentation(batch), "Aegis 已完成远程 IP 研判，请在卡片中继续。"),
        };
      } catch (error) {
        api.logger.warn(`aegis-tools analysis card failed: ${error instanceof Error ? error.message : String(error)}`);
        return {
          handled: true,
          reason: "aegis-ip-card-error",
          reply: {
            isError: true,
            ...cardReply(errorPresentation(error), "Aegis IP 分析失败，请查看卡片详情。"),
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

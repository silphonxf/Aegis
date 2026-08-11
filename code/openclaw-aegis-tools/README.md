# OpenClaw Aegis Tools

This OpenClaw plugin exposes Aegis IP analysis and controlled firewall blocking
as interactive Feishu cards. Messages containing IPv4 addresses are handled
before the model runs, producing a deterministic analyze → prepare → confirm →
execute card workflow. It reads the sender from OpenClaw's trusted
`requesterSenderId` runtime context; the model cannot provide or override an
`open_id` tool argument.

The analysis card presents one or more IPs as an intelligence list. The Feishu
user can select or unselect individual IPs, review the selected count, and then
confirm exactly that subset before any dry-run or permanent block is possible.
Each item also shows the ThreatBook location, carrier, ASN, attack types,
judgments/tags, severity, confidence, risk score, and evidence summary. When
ThreatBook does not return an attack classification, the card says so instead
of guessing one.

The plugin also registers a trusted tool policy that blocks local firewall
commands from Feishu runs. IP blocking therefore cannot silently fall back to
`iptables`, `nft`, `ufw`, Hillstone APIs, or another local shell path.

## Build the distributable archive

Build and pack from the Aegis repository. `prepack` always rebuilds
`dist/index.js`, so the archive cannot accidentally contain stale TypeScript
output.

```bash
cd code/openclaw-aegis-tools
npm ci
npm audit --omit=dev
npm pack
```

Copy the resulting versioned `openclaw-aegis-tools-*.tgz` to the remote
OpenClaw server. Do not copy `openclaw.json`, gateway tokens, CA private keys,
or local `.env` files with it.

## Install on the remote OpenClaw server

Install the generated npm tarball on that server, then run:

```bash
openclaw plugins install ./openclaw-aegis-tools-1.3.0.tgz
```

The distributable tarball includes `dist/index.js`, which is required by
OpenClaw package installs. TypeScript source is retained for review.

Configure the plugin in `openclaw.json`:

```json5
{
  plugins: {
    // Preserve every plugin already allowed on this OpenClaw server and add
    // aegis-tools; do not replace the list with only this plugin.
    allow: ["aegis-tools", "feishu"],
    entries: {
      "aegis-tools": {
        enabled: true,
        hooks: {
          allowConversationAccess: true,
        },
        config: {
          baseUrl: "https://AEGIS_HOST:18791",
          token: "THE_SAME_LONG_RANDOM_TOKEN_AS_AEGIS",
          caFile: "/etc/openclaw/aegis-ca.crt",
          timeoutMs: 30000,
        },
      },
    },
  },
  tools: {
    alsoAllow: ["aegis-tools"],
  },
}
```

Use a trusted public/private CA certificate whenever possible. For a temporary
closed-network test with a self-signed certificate, set `allowInsecureTls: true`
instead of `caFile`, then restore certificate verification before production.

Restart the OpenClaw gateway after installing or changing plugin configuration.

Verify the runtime contract rather than relying only on the installed-plugin
directory:

```bash
openclaw plugins inspect aegis-tools
openclaw gateway call tools.catalog --params '{"agentId":"main","includePlugins":true}'
openclaw gateway call commands.list
```

The catalog must contain all five `aegis_ip_*` tools and the command list must
contain `aegis-ip`.

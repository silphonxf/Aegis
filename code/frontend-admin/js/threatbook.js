window.AegisAdmin = window.AegisAdmin || {};

(function (ns) {
  let latestResult = null;
  let displayedItems = [];

  function escapeHtml(value) {
    return String(value ?? '')
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#39;');
  }

  function riskClass(level) {
    if (level === 'high_risk') return 'red';
    if (level === 'medium_risk' || level === 'suspicious') return 'yellow';
    return 'green';
  }

  function renderTable(items) {
    displayedItems = items || [];
    const tbody = document.getElementById('threatbookResultTbody');
    if (!tbody) return;
    const rows = displayedItems.map((item) => `
      <tr>
        <td>${escapeHtml(item.resource || item.ip || item.domain)}</td>
        <td>${item.resource_type === 'domain' ? '域名' : 'IP'}</td>
        <td>${escapeHtml(item.ip_type || item.domain_type || '-')}</td>
        <td>${escapeHtml(item.country || '-')}</td>
        <td>${escapeHtml((item.malicious_types || []).join('、') || '-')}</td>
        <td><span class="status-chip ${riskClass(item.risk_level)}">${escapeHtml(item.risk_level)}</span></td>
        <td>${item.is_malicious ? '是' : '否'}</td>
      </tr>
    `).join('');
    tbody.innerHTML = rows || '<tr><td colspan="7">暂无结果</td></tr>';
  }

  function getAllItems() {
    return latestResult?.items || [];
  }

  function getAutoBlockItems() {
    return getAllItems().filter((item) => item.should_block);
  }

  function updateSummaryCards(data) {
    const blockCount = getAutoBlockItems().length;
    const totalEl = document.getElementById('threatbookTotal');
    const maliciousEl = document.getElementById('threatbookMalicious');
    const blockEl = document.getElementById('threatbookBlockCandidates');
    if (totalEl) totalEl.textContent = data?.summary?.total ?? 0;
    if (maliciousEl) maliciousEl.textContent = data?.summary?.malicious ?? 0;
    if (blockEl) blockEl.textContent = blockCount;
  }

  function renderResultText(data, extra = '') {
    const blockCandidates = getAutoBlockItems().map((i) => i.ip).join(', ') || '无';
    updateSummaryCards(data);
    const resultEl = document.getElementById('threatbookResult');
    if (!resultEl) return;
    resultEl.textContent = [
      `查询总数：${data.summary?.total ?? 0}`,
      `IP：${data.summary?.ip_count ?? 0}，域名：${data.summary?.domain_count ?? 0}`,
      `恶意目标：${data.summary?.malicious ?? 0}`,
      `高危目标：${data.summary?.high_risk ?? 0}`,
      `封禁候选：${blockCandidates}`,
      extra,
    ].filter(Boolean).join('\n');
  }

  function renderResult() {
    if (latestResult) {
      renderTable(getAllItems());
      renderResultText(latestResult);
    }
  }

  function setValue(id, value) {
    const el = document.getElementById(id);
    if (el) el.value = value ?? '';
  }

  function setFirewallConfigSummary(data) {
    const el = document.getElementById('threatbookFirewallConfigSummary');
    if (!el) return;
    if (!data) {
      el.textContent = '防火墙配置未读取';
      return;
    }
    const authState = data.has_username && data.has_password ? '账号密码已配置' : '账号密码未完整配置';
    el.textContent = `${data.enabled ? '已启用' : '已停用'} / ${data.target_name || data.target_code || '默认设备'} / ${data.firewall_ip || '-'} / ${data.address_book_name || '-'} / ${authState}`;
  }

  function fillFirewallConfigModal(data) {
    setValue('modalFirewallTargetCode', data.target_code || 'test-primary');
    setValue('modalFirewallTargetName', data.target_name || '山石测试设备');
    setValue('modalFirewallIsDefault', data.is_default === false ? 'false' : 'true');
    setValue('modalFirewallIsTestTarget', data.is_test_target === false ? 'false' : 'true');
    setValue('modalFirewallEnabled', data.enabled === false ? 'false' : 'true');
    setValue('modalFirewallScheme', data.scheme || 'https');
    setValue('modalFirewallPort', data.port || 443);
    setValue('modalFirewallIp', data.firewall_ip || '');
    setValue('modalFirewallAddressBook', data.address_book_name || '');
    setValue('modalFirewallUsername', '');
    setValue('modalFirewallPassword', '');
    setValue('modalFirewallVerifySsl', data.verify_ssl ? 'true' : 'false');
    setValue('modalFirewallTimeout', data.timeout_seconds || 15);
    setValue('modalFirewallAddrbookPath', data.addrbook_path || '/api/addrbook');
    const secretEl = document.getElementById('modalFirewallSecretSummary');
    if (secretEl) {
      const usernameText = data.has_username ? '账号已保存' : '账号未保存';
      const passwordText = data.has_password ? '密码已保存' : '密码未保存';
      secretEl.textContent = `${usernameText}，${passwordText}。账号和密码不回显，输入新值才会覆盖。`;
    }
  }

  async function loadFirewallConfig() {
    const data = await ns.api.request('/api/v1/admin/threat-intel/firewall-config', {
      headers: ns.api.headers(),
    });
    setFirewallConfigSummary(data);
    return data;
  }

  async function openFirewallConfigModal() {
    const data = await loadFirewallConfig();
    fillFirewallConfigModal(data);
    ns.modals.openModal('firewallConfigModal');
  }

  async function saveFirewallConfig() {
    const username = document.getElementById('modalFirewallUsername')?.value ?? '';
    const password = document.getElementById('modalFirewallPassword')?.value ?? '';
    const payload = {
      target_code: document.getElementById('modalFirewallTargetCode')?.value.trim() || 'test-primary',
      target_name: document.getElementById('modalFirewallTargetName')?.value.trim() || '山石测试设备',
      is_default: (document.getElementById('modalFirewallIsDefault')?.value || 'true') === 'true',
      is_test_target: (document.getElementById('modalFirewallIsTestTarget')?.value || 'true') === 'true',
      enabled: (document.getElementById('modalFirewallEnabled')?.value || 'true') === 'true',
      scheme: document.getElementById('modalFirewallScheme')?.value || 'https',
      firewall_ip: document.getElementById('modalFirewallIp')?.value.trim() || '',
      port: Number(document.getElementById('modalFirewallPort')?.value || 443),
      address_book_name: document.getElementById('modalFirewallAddressBook')?.value.trim() || '',
      verify_ssl: (document.getElementById('modalFirewallVerifySsl')?.value || 'false') === 'true',
      timeout_seconds: Number(document.getElementById('modalFirewallTimeout')?.value || 15),
      addrbook_path: document.getElementById('modalFirewallAddrbookPath')?.value.trim() || '/api/addrbook',
    };
    if (username.trim()) payload.username = username.trim();
    if (password) payload.password = password;
    const data = await ns.api.request('/api/v1/admin/threat-intel/firewall-config', {
      method: 'PUT',
      headers: ns.api.headers(),
      body: JSON.stringify(payload),
    });
    setFirewallConfigSummary(data);
    fillFirewallConfigModal(data);
    ns.modals.closeModal('firewallConfigModal');
    const resultEl = document.getElementById('threatbookResult');
    if (resultEl) resultEl.textContent = `${resultEl.textContent}\n\n--- 防火墙配置已保存 ---\n账号密码已加密保存，界面不回显。`;
    return data;
  }

  async function queryThreatbook() {
    const rawInput = document.getElementById('threatbookRawInput')?.value || '';
    const lang = document.getElementById('threatbookLang')?.value || 'zh';
    const realtimeVerdict = (document.getElementById('threatbookRealtimeVerdict')?.value || 'true') === 'true';
    const data = await ns.api.request('/api/v1/admin/threat-intel/analyze', {
      method: 'POST',
      headers: ns.api.headers(),
      body: JSON.stringify({ raw_input: rawInput, lang, realtime_verdict: realtimeVerdict }),
    });
    latestResult = data;
    renderResult();
    return data;
  }

  async function blockIp(ip, reason, riskLevel = 'high_risk') {
    const targetIp = ip || document.getElementById('threatbookBlockIp')?.value.trim();
    const inputReason = document.getElementById('threatbookBlockReason')?.value.trim() || null;
    const targetReason = reason ?? inputReason;
    const dryRun = document.getElementById('threatbookFirewallDryRun')?.checked ?? true;
    if (!targetIp) throw new Error('请先输入要封禁的 IP');
    const data = await ns.api.request('/api/v1/admin/threat-intel/block-ip', {
      method: 'POST',
      headers: ns.api.headers(),
      body: JSON.stringify({ ip: targetIp, reason: targetReason, risk_level: riskLevel, source: 'threatbook', dry_run: dryRun }),
    });
    const resultEl = document.getElementById('threatbookResult');
    resultEl.textContent = `${resultEl.textContent}\n\n--- ${dryRun ? '演练封禁返回' : '防火墙封禁返回'} ---\n${JSON.stringify(data, null, 2)}`;
    return data;
  }

  async function batchBlockAutoCandidates() {
    const items = getAutoBlockItems();
    if (!items.length) throw new Error('当前没有可自动封禁的 IP');
    const results = [];
    for (const item of items) {
      const data = await blockIp(item.ip, `自动封禁候选：${item.summary || 'ThreatBook 命中高危规则'}`, item.risk_level || 'high_risk');
      results.push(data);
    }
    const resultEl = document.getElementById('threatbookResult');
    resultEl.textContent = `${resultEl.textContent}\n\n--- 批量封禁汇总 ---\n${JSON.stringify(results, null, 2)}`;
    return results;
  }

  function fillDemo() {
    const input = document.getElementById('threatbookRawInput');
    if (input) input.value = '66.240.205.34\n8.8.8.8\nexample.com\nbibme.org';
  }

  function fillBindingForm(item) {
    setValue('feishuBindingOpenId', item.open_id);
    setValue('feishuBindingDisplayName', item.display_name || '');
    setValue('feishuBindingAegisUserId', item.aegis_user_id || '');
    setValue('feishuBindingEnabled', item.enabled ? 'true' : 'false');
    const queryEl = document.getElementById('feishuBindingCanQuery');
    const blockEl = document.getElementById('feishuBindingCanBlock');
    if (queryEl) queryEl.checked = Boolean(item.can_query);
    if (blockEl) blockEl.checked = Boolean(item.can_block);
  }

  async function loadFeishuBindings() {
    const data = await ns.api.request('/api/v1/admin/security-response/feishu-bindings', {
      headers: ns.api.headers(),
    });
    const items = data.items || [];
    const tbody = document.getElementById('feishuBindingTbody');
    if (tbody) {
      tbody.innerHTML = items.map((item) => `
        <tr>
          <td>${escapeHtml(item.display_name || '-')}</td>
          <td><code>${escapeHtml(item.open_id)}</code></td>
          <td>${escapeHtml(item.aegis_user_id || '-')}</td>
          <td>${item.can_query ? '是' : '否'}</td>
          <td>${item.can_block ? '是' : '否'}</td>
          <td>${item.enabled ? '启用' : '停用'}</td>
          <td><button class="toolbar-btn secondary" type="button" data-feishu-open-id="${escapeHtml(item.open_id)}">编辑</button></td>
        </tr>
      `).join('') || '<tr><td colspan="7">暂无数据；请先给机器人发一条消息。</td></tr>';
      tbody.querySelectorAll('[data-feishu-open-id]').forEach((button) => {
        button.onclick = () => fillBindingForm(items.find((item) => item.open_id === button.dataset.feishuOpenId));
      });
    }
    const summary = document.getElementById('feishuBindingSummary');
    if (summary) summary.textContent = `已登记 ${items.length} 个飞书身份；拥有封禁权限 ${items.filter((item) => item.enabled && item.can_block).length} 个。`;
    return data;
  }

  async function saveFeishuBinding() {
    const openId = document.getElementById('feishuBindingOpenId')?.value.trim() || '';
    const aegisUserIdRaw = document.getElementById('feishuBindingAegisUserId')?.value || '';
    if (!openId) throw new Error('请填写飞书 open_id');
    const payload = {
      open_id: openId,
      display_name: document.getElementById('feishuBindingDisplayName')?.value.trim() || null,
      aegis_user_id: aegisUserIdRaw ? Number(aegisUserIdRaw) : null,
      can_query: document.getElementById('feishuBindingCanQuery')?.checked ?? false,
      can_block: document.getElementById('feishuBindingCanBlock')?.checked ?? false,
      enabled: (document.getElementById('feishuBindingEnabled')?.value || 'true') === 'true',
    };
    await ns.api.request('/api/v1/admin/security-response/feishu-bindings', {
      method: 'PUT',
      headers: ns.api.headers(),
      body: JSON.stringify(payload),
    });
    return loadFeishuBindings();
  }

  ns.threatbook = {
    queryThreatbook,
    blockIp,
    batchBlockAutoCandidates,
    fillDemo,
    loadFirewallConfig,
    openFirewallConfigModal,
    saveFirewallConfig,
    loadFeishuBindings,
    saveFeishuBinding,
    renderTable,
    getAutoBlockItems,
  };
})(window.AegisAdmin);

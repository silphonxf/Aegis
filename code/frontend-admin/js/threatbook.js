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
        <td>${escapeHtml(item.ip)}</td>
        <td><span class="status-chip ${riskClass(item.risk_level)}">${escapeHtml(item.risk_level)}</span></td>
        <td>${item.is_malicious ? '是' : '否'}</td>
        <td>${escapeHtml(item.decision || '-')}</td>
        <td>${escapeHtml(item.summary || '-')}</td>
      </tr>
    `).join('');
    tbody.innerHTML = rows || '<tr><td colspan="5">暂无结果</td></tr>';
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
      `恶意 IP：${data.summary?.malicious ?? 0}`,
      `高危 IP：${data.summary?.high_risk ?? 0}`,
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

  async function queryThreatbook() {
    const rawInput = document.getElementById('threatbookRawInput')?.value || '';
    const lang = document.getElementById('threatbookLang')?.value || 'zh';
    const realtimeVerdict = (document.getElementById('threatbookRealtimeVerdict')?.value || 'true') === 'true';
    const data = await ns.api.request('/api/v1/admin/threat-intel/ip-reputation/quick', {
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
    if (input) input.value = '66.240.205.34\n8.8.8.8\n1.1.1.1';
  }

  ns.threatbook = {
    queryThreatbook,
    blockIp,
    batchBlockAutoCandidates,
    fillDemo,
    renderTable,
    getAutoBlockItems,
  };
})(window.AegisAdmin);

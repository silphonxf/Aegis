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
        <td>${escapeHtml(item.severity || '-')}</td>
        <td>${escapeHtml(item.confidence_level || '-')}</td>
        <td>${escapeHtml(item.decision || '-')}</td>
        <td>${escapeHtml(item.summary || '-')}</td>
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

  function getManualConfirmItems() {
    return getAllItems().filter((item) => item.needs_manual_confirmation);
  }

  function getMaliciousItems() {
    return getAllItems().filter((item) => item.is_malicious);
  }

  function filterItems(mode) {
    if (mode === 'auto_block') return getAutoBlockItems();
    if (mode === 'manual_confirm') return getManualConfirmItems();
    if (mode === 'malicious') return getMaliciousItems();
    return getAllItems();
  }

  function renderResultText(data, extra = '') {
    const blockCandidates = getAutoBlockItems().map((i) => i.ip).join(', ') || '无';
    const confirmCandidates = getManualConfirmItems().map((i) => i.ip).join(', ') || '无';
    document.getElementById('threatbookResult').textContent = [
      `查询总数：${data.summary?.total ?? 0}`,
      `恶意 IP：${data.summary?.malicious ?? 0}`,
      `高危 IP：${data.summary?.high_risk ?? 0}`,
      `自动封禁候选：${blockCandidates}`,
      `需二次确认（济南）：${confirmCandidates}`,
      `当前表格展示：${displayedItems.length} 条`,
      extra,
      '',
      JSON.stringify(data, null, 2),
    ].filter(Boolean).join('\n');
  }

  function applyFilter() {
    if (!latestResult) {
      document.getElementById('threatbookResult').textContent = '暂无查询结果，无法筛选';
      return;
    }
    const mode = document.getElementById('threatbookResultFilter')?.value || 'all';
    const items = filterItems(mode);
    renderTable(items);
    renderResultText(latestResult, `当前筛选：${mode}`);
  }

  function resetFilter() {
    const filter = document.getElementById('threatbookResultFilter');
    if (filter) filter.value = 'all';
    if (latestResult) {
      renderTable(getAllItems());
      renderResultText(latestResult, '当前筛选：all');
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
    resetFilter();
    return data;
  }

  async function uploadExcel() {
    const fileInput = document.getElementById('threatbookExcelFile');
    const file = fileInput?.files?.[0];
    if (!file) throw new Error('请先选择 Excel 文件');
    const lang = document.getElementById('threatbookLang')?.value || 'zh';
    const realtimeVerdict = (document.getElementById('threatbookRealtimeVerdict')?.value || 'true') === 'true';
    const form = new FormData();
    form.append('file', file);
    const resp = await fetch(`${ns.api.base()}/api/v1/admin/threat-intel/ip-reputation/excel?lang=${encodeURIComponent(lang)}&realtime_verdict=${realtimeVerdict}`, {
      method: 'POST',
      headers: ns.state.token ? { Authorization: `Bearer ${ns.state.token}` } : {},
      body: form,
    });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      throw new Error(data?.message || `HTTP ${resp.status}`);
    }
    latestResult = data;
    resetFilter();
    renderResultText(data, `导入文件：${data.import?.filename || file.name}`);
    return data;
  }

  async function blockIp(ip, reason, riskLevel = 'high_risk') {
    const targetIp = ip || document.getElementById('threatbookBlockIp')?.value.trim();
    const inputReason = document.getElementById('threatbookBlockReason')?.value.trim() || null;
    const targetReason = reason ?? inputReason;
    if (!targetIp) throw new Error('请先输入要封禁的 IP');
    const data = await ns.api.request('/api/v1/admin/threat-intel/block-ip', {
      method: 'POST',
      headers: ns.api.headers(),
      body: JSON.stringify({ ip: targetIp, reason: targetReason, risk_level: riskLevel, source: 'threatbook', dry_run: true }),
    });
    const resultEl = document.getElementById('threatbookResult');
    resultEl.textContent = `${resultEl.textContent}\n\n--- 模拟封禁返回 ---\n${JSON.stringify(data, null, 2)}`;
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
    resultEl.textContent = `${resultEl.textContent}\n\n--- 批量模拟封禁汇总 ---\n${JSON.stringify(results, null, 2)}`;
    return results;
  }

  function fillDemo() {
    const input = document.getElementById('threatbookRawInput');
    if (input) input.value = '8.8.8.8\n1.1.1.1\n127.0.0.1';
  }

  function exportJson() {
    if (!latestResult) {
      document.getElementById('threatbookResult').textContent = '暂无可导出的查询结果';
      return;
    }
    const blob = new Blob([JSON.stringify(latestResult, null, 2)], { type: 'application/json;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `threatbook-ip-result-${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  ns.threatbook = {
    queryThreatbook,
    uploadExcel,
    blockIp,
    batchBlockAutoCandidates,
    fillDemo,
    exportJson,
    renderTable,
    applyFilter,
    resetFilter,
    getAutoBlockItems,
    getManualConfirmItems,
  };
})(window.AegisAdmin);

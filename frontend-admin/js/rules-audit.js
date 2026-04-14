window.AegisAdmin = window.AegisAdmin || {};

(function (ns) {
  function buildAuditQuery() {
    const params = new URLSearchParams({ page: '1', size: '20' });
    const mappings = [
      ['auditAction', 'action'],
      ['auditUsername', 'username'],
      ['auditResource', 'resource'],
      ['auditStartAt', 'start_at'],
      ['auditEndAt', 'end_at'],
      ['auditKeyword', 'keyword'],
    ];
    mappings.forEach(([id, key]) => {
      const value = document.getElementById(id)?.value.trim();
      if (value) params.set(key, value);
    });
    return params.toString();
  }

  async function loadRules() {
    const r = await ns.api.request('/api/v1/monitoring/rules', { headers: ns.api.headers() });
    document.getElementById('cpuWarn').value = r.cpu_warn;
    document.getElementById('cpuCritical').value = r.cpu_critical;
    document.getElementById('memWarn').value = r.mem_warn;
    document.getElementById('memCritical').value = r.mem_critical;
    document.getElementById('diskWarn').value = r.disk_warn;
    document.getElementById('diskCritical').value = r.disk_critical;
    document.getElementById('ruleResult').textContent = JSON.stringify(r, null, 2);
    return r;
  }

  async function saveRules() {
    const payload = {
      cpu_warn: Number(document.getElementById('cpuWarn').value),
      cpu_critical: Number(document.getElementById('cpuCritical').value),
      mem_warn: Number(document.getElementById('memWarn').value),
      mem_critical: Number(document.getElementById('memCritical').value),
      disk_warn: Number(document.getElementById('diskWarn').value),
      disk_critical: Number(document.getElementById('diskCritical').value),
    };
    const d = await ns.api.request('/api/v1/monitoring/rules', { method: 'PUT', headers: ns.api.headers(), body: JSON.stringify(payload) });
    document.getElementById('ruleResult').textContent = JSON.stringify({ ...d, payload }, null, 2);
    return d;
  }

  async function loadAudit() {
    const qs = buildAuditQuery();
    const data = await ns.api.request(`/api/v1/admin/audit-logs?${qs}`, { headers: ns.api.headers() });
    document.getElementById('audit').textContent = JSON.stringify(data, null, 2);
    return data;
  }

  ns.rulesAudit = { buildAuditQuery, loadRules, saveRules, loadAudit };
})(window.AegisAdmin);

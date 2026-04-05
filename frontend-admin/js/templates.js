window.AegisAdmin = window.AegisAdmin || {};

(function (ns) {
  async function createTemplate() {
    const d = await ns.api.request('/api/v1/selfchecks/templates', {
      method: 'POST',
      headers: ns.api.headers(),
      body: JSON.stringify({
        system_id: Number(document.getElementById('tplSystemId').value),
        check_type: document.getElementById('tplCheckType').value,
        name: document.getElementById('tplName').value,
      }),
    });
    document.getElementById('templateCreateResult').textContent = JSON.stringify(d, null, 2);
    return d;
  }

  async function listTemplates() {
    const d = await ns.api.request('/api/v1/selfchecks/templates?page=1&size=50', { headers: ns.api.headers() });
    document.getElementById('templateListResult').textContent = JSON.stringify(d, null, 2);
    return d;
  }

  async function createSnapshot() {
    const sid = Number(document.getElementById('snapSystemId').value);
    const d = await ns.api.request(`/api/v1/systems/${sid}/status/snapshot`, {
      method: 'POST',
      headers: ns.api.headers(),
      body: JSON.stringify({
        host_online: document.getElementById('snapHostOnline').value || 'unknown',
        port_ok: document.getElementById('snapPortOk').value || 'unknown',
        cpu_usage: Number(document.getElementById('snapCpu').value),
        mem_usage: Number(document.getElementById('snapMem').value),
        disk_usage: Number(document.getElementById('snapDisk').value),
        last_inspection_result: 'normal',
        last_selfcheck_result: document.getElementById('snapSelfcheck').value || 'unknown',
      }),
    });
    document.getElementById('snapshotResult').textContent = JSON.stringify(d, null, 2);
    return d;
  }

  ns.templates = { createTemplate, listTemplates, createSnapshot };
})(window.AegisAdmin);

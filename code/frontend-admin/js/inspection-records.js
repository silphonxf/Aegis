window.AegisAdmin = window.AegisAdmin || {};

(function (ns) {
  function escape(value) {
    return ns.toolbox.escapeHtml(value ?? '');
  }

  function value(id) {
    return document.getElementById(id)?.value?.trim() || '';
  }

  function appendParam(params, key, val) {
    if (val !== '') params.set(key, val);
  }

  function formatTime(value) {
    if (!value) return '-';
    return String(value).replace('T', ' ').slice(0, 19);
  }

  function resultLabel(value) {
    const map = { normal: '正常', abnormal: '异常' };
    return map[value] || value || '-';
  }

  function renderCheckResults(items) {
    const rows = Array.isArray(items) ? items : [];
    if (!rows.length) return '-';
    return rows.map((item) => {
      const name = item.item || item.name || '-';
      const result = resultLabel(item.result);
      return `${escape(name)}：${escape(result)}`;
    }).join('<br>');
  }

  function renderRecords(items) {
    const tbody = document.getElementById('inspectionRecordTbody');
    if (!tbody) return;
    const rows = (items || []).map((item) => `
      <tr>
        <td>${escape(item.id)}</td>
        <td>${escape(item.system_name || item.system_id || '-')}</td>
        <td>${escape(item.room_name || item.room_id || '-')}</td>
        <td>${escape(item.point_name || item.point_code || item.point_id || '-')}</td>
        <td>${escape(item.inspector_name || item.inspector_id || '-')}</td>
        <td><span class="status-chip ${item.result === 'abnormal' ? 'failed' : 'done'}">${escape(resultLabel(item.result))}</span></td>
        <td>${escape(item.source || '-')}</td>
        <td>${escape(formatTime(item.inspected_at))}</td>
        <td>${renderCheckResults(item.check_results)}</td>
        <td>${escape(item.note || '-')}</td>
      </tr>
    `).join('');
    tbody.innerHTML = rows || '<tr><td colspan="10">暂无巡检记录</td></tr>';
  }

  function buildQuery() {
    const params = new URLSearchParams({ page: '1', size: '50' });
    appendParam(params, 'system_id', value('inspectionRecordSystemId'));
    appendParam(params, 'room_id', value('inspectionRecordRoomId'));
    appendParam(params, 'point_id', value('inspectionRecordPointId'));
    appendParam(params, 'result', value('inspectionRecordResult'));
    appendParam(params, 'start_at', value('inspectionRecordStartAt'));
    appendParam(params, 'end_at', value('inspectionRecordEndAt'));
    return params.toString();
  }

  async function listInspectionRecords() {
    const data = await ns.api.request(`/api/v1/admin/inspection-records?${buildQuery()}`, { headers: ns.api.headers() });
    const items = Array.isArray(data.items) ? data.items : [];
    renderRecords(items);
    const summary = document.getElementById('inspectionRecordSummary');
    if (summary) summary.textContent = `显示 ${items.length} 条，共 ${data.total ?? items.length} 条巡检记录`;
    const raw = document.getElementById('inspectionRecordRaw');
    if (raw) raw.textContent = JSON.stringify(data, null, 2);
    return data;
  }

  function clearFilters() {
    [
      'inspectionRecordSystemId',
      'inspectionRecordRoomId',
      'inspectionRecordPointId',
      'inspectionRecordResult',
      'inspectionRecordStartAt',
      'inspectionRecordEndAt',
    ].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.value = '';
    });
    return listInspectionRecords();
  }

  ns.inspectionRecords = { listInspectionRecords, clearFilters, renderRecords };
})(window.AegisAdmin);

window.AegisAdmin = window.AegisAdmin || {};

(function (ns) {
  function escapeHtml(value) {
    return String(value ?? '')
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#39;');
  }

  function renderToolTaskTable(items) {
    const tbody = document.getElementById('toolTaskTbody');
    if (!tbody) return;
    const rows = (items || []).map((task) => {
      const result = task.result || {};
      const successText = result.success === true ? 'success' : result.success === false ? 'failed' : '-';
      const timeText = task.finished_at || task.started_at || task.created_at || '-';
      const noteText = result.note || result.reason || result.error || '-';
      const status = String(task.status || 'unknown').toLowerCase();
      return `
        <tr>
          <td>${escapeHtml(task.id)}</td>
          <td>${escapeHtml(task.action || '-')}</td>
          <td>${escapeHtml(task.target || '-')}</td>
          <td><span class="status-chip ${escapeHtml(status)}">${escapeHtml(task.status || '-')}</span> / ${escapeHtml(successText)}</td>
          <td>${escapeHtml(task.executor || result.executor || '-')}</td>
          <td>${escapeHtml(timeText)}</td>
          <td>${escapeHtml(noteText)}</td>
        </tr>
      `;
    }).join('');
    tbody.innerHTML = rows || '<tr><td colspan="7">暂无任务</td></tr>';
  }

  function formatTaskRow(task) {
    const result = task.result || {};
    return [
      `#${task.id} ${task.action} @ ${task.target}`,
      `status=${task.status}`,
      `executor=${task.executor || result.executor || '-'}`,
      `success=${result.success === true ? 'true' : result.success === false ? 'false' : '-'}`,
      `started_at=${task.started_at || result.started_at || '-'}`,
      `finished_at=${task.finished_at || result.finished_at || '-'}`,
      `reason=${result.reason || '-'}`,
      `note=${result.note || '-'}`,
      `error=${result.error || '-'}`,
    ].join('\n');
  }

  async function listTasks() {
    const s = document.getElementById('toolTaskStatusFilter')?.value.trim() || '';
    const q = s ? `?page=1&size=50&status=${encodeURIComponent(s)}` : '?page=1&size=50';
    const d = await ns.api.request(`/api/v1/toolbox/tasks${q}`, { headers: ns.api.headers() });
    renderToolTaskTable(d.items || []);
    const items = (d.items || []).map(formatTaskRow).join('\n\n----------------\n\n');
    const resultEl = document.getElementById('toolTaskResult');
    if (resultEl) resultEl.textContent = `共 ${d.total ?? d.items?.length ?? 0} 条\n\n${items || '暂无任务'}`;
    return d;
  }

  async function updateTask() {
    const taskId = Number(document.getElementById('toolTaskId')?.value);
    const d = await ns.api.request(`/api/v1/toolbox/tasks/${taskId}/status`, {
      method: 'PUT',
      headers: ns.api.headers(),
      body: JSON.stringify({
        status: document.getElementById('toolTaskActionStatus')?.value,
        note: document.getElementById('toolTaskNote')?.value || null,
        executor: 'admin-console',
      }),
    });
    const resultEl = document.getElementById('toolTaskResult');
    if (resultEl) resultEl.textContent = `状态更新成功\n${JSON.stringify(d, null, 2)}`;
    await listTasks();
    return d;
  }

  ns.toolbox = { escapeHtml, renderToolTaskTable, formatTaskRow, listTasks, updateTask };
})(window.AegisAdmin);

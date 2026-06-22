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

  function renderTaskActions(task) {
    const status = String(task.status || '').toLowerCase();
    const actionsByStatus = {
      pending_approval: [
        ['approved', '通过', '审批通过'],
        ['rejected', '驳回', '审批驳回'],
        ['cancelled', '取消', '审批取消'],
      ],
      approved: [
        ['running', '开始', '开始执行'],
        ['cancelled', '取消', '执行前取消'],
      ],
      running: [
        ['done', '完成', '执行完成'],
        ['failed', '失败', '执行失败'],
        ['cancelled', '取消', '执行中取消'],
      ],
    };
    const actions = actionsByStatus[status] || [];
    if (!actions.length) return '<span class="muted-cell">无可用操作</span>';
    return actions.map(([nextStatus, label, note]) => {
      const danger = ['rejected', 'failed', 'cancelled'].includes(nextStatus) ? ' danger' : '';
      return `
        <button
          type="button"
          class="table-action-btn task-action-btn${danger}"
          data-task-id="${escapeHtml(task.id)}"
          data-task-next-status="${escapeHtml(nextStatus)}"
          data-task-note="${escapeHtml(note)}"
        >${escapeHtml(label)}</button>
      `;
    }).join('');
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
      const actions = renderTaskActions(task);
      return `
        <tr>
          <td>${escapeHtml(task.id)}</td>
          <td>${escapeHtml(task.action || '-')}</td>
          <td>${escapeHtml(task.target || '-')}</td>
          <td><span class="status-chip ${escapeHtml(status)}">${escapeHtml(task.status || '-')}</span> / ${escapeHtml(successText)}</td>
          <td>${escapeHtml(task.executor || result.executor || '-')}</td>
          <td>${escapeHtml(timeText)}</td>
          <td>${escapeHtml(noteText)}</td>
          <td><div class="task-action-row">${actions}</div></td>
        </tr>
      `;
    }).join('');
    tbody.innerHTML = rows || '<tr><td colspan="8">暂无任务</td></tr>';
    tbody.querySelectorAll('[data-task-next-status]').forEach((btn) => {
      btn.addEventListener('click', () => {
        quickUpdateTask(btn.dataset.taskId, btn.dataset.taskNextStatus, btn.dataset.taskNote || '').catch((e) => {
          const resultEl = document.getElementById('toolTaskResult');
          if (resultEl) resultEl.textContent = `状态更新失败：${e.message}`;
        });
      });
    });
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
    if (!taskId) throw new Error('请先输入 task_id');
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

  async function quickUpdateTask(taskId, status, note) {
    const idInput = document.getElementById('toolTaskId');
    const statusInput = document.getElementById('toolTaskActionStatus');
    const noteInput = document.getElementById('toolTaskNote');
    if (idInput) idInput.value = taskId;
    if (statusInput) statusInput.value = status;
    if (noteInput && !noteInput.value.trim()) noteInput.value = note;
    return updateTask();
  }

  function setPingBusyNotice(visible) {
    let notice = document.getElementById('netPingBusyNotice');
    if (visible) {
      if (!notice) {
        notice = document.createElement('div');
        notice.id = 'netPingBusyNotice';
        notice.className = 'inline-busy-notice';
        notice.textContent = '正在进行检测请稍等';
        document.body.appendChild(notice);
      }
      notice.classList.remove('hidden');
      return;
    }
    notice?.classList.add('hidden');
  }


  async function runNetworkPing() {
    const host = document.getElementById('netPingHost')?.value.trim();
    const count = Number(document.getElementById('netPingCount')?.value || 1);
    const button = document.getElementById('btnNetPingRun');
    if (!host) throw new Error('请先输入 Ping 目标地址');
    if (button?.disabled) return null;
    const originalText = button?.textContent || '执行 Ping';
    if (button) {
      button.disabled = true;
      button.textContent = '检测中...';
    }
    setPingBusyNotice(true);
    try {
      const data = await ns.api.request('/api/v1/toolbox/ping', {
        method: 'POST',
        headers: ns.api.headers(),
        body: JSON.stringify({ host, count }),
      });
      const statusText = data.ok ? '接通' : '可能异常';
      const targetEl = document.getElementById('netPingTarget');
      const statusEl = document.getElementById('netPingStatus');
      const latencyEl = document.getElementById('netPingLatency');
      const packetLossEl = document.getElementById('netPingPacketLoss');
      const resultEl = document.getElementById('netPingResult');
      const packetStats = data.packet_stats || {};
      if (targetEl) targetEl.textContent = data.host || host;
      if (statusEl) statusEl.textContent = statusText;
      if (latencyEl) latencyEl.textContent = `${data.latency_ms ?? 0} ms`;
      if (packetLossEl) {
        const sent = packetStats.sent ?? data.count ?? count;
        const received = packetStats.received ?? '-';
        const loss = packetStats.loss_percent ?? '-';
        packetLossEl.textContent = `${received}/${sent}，丢包 ${loss}%`;
      }
      if (resultEl) resultEl.textContent = JSON.stringify(data, null, 2);
      return data;
    } finally {
      if (button) {
        button.disabled = false;
        button.textContent = originalText;
      }
      setPingBusyNotice(false);
    }
  }

  async function fetchNetworkCapture() {
    const url = document.getElementById('netCaptureUrl')?.value.trim();
    const note = document.getElementById('netCaptureNote')?.value.trim() || null;
    if (!url) throw new Error('请先输入要抓取的 URL');
    const data = await ns.api.request('/api/v1/toolbox/capture/fetch', {
      method: 'POST',
      headers: ns.api.headers(),
      body: JSON.stringify({ url, note }),
    });
    const contentEl = document.getElementById('netCaptureContent');
    const statusEl = document.getElementById('netCaptureStatus');
    const latencyEl = document.getElementById('netCaptureLatency');
    const resultEl = document.getElementById('netCaptureResult');
    if (contentEl) contentEl.value = data.content || '';
    if (statusEl) statusEl.textContent = data.status_code ? `HTTP ${data.status_code}` : '--';
    if (latencyEl) latencyEl.textContent = `${data.elapsed_ms ?? 0} ms`;
    if (resultEl) resultEl.textContent = JSON.stringify(data, null, 2);
    return data;
  }

  async function analyzeNetworkCapture() {
    const content = document.getElementById('netCaptureContent')?.value.trim();
    const targetUrl = document.getElementById('netCaptureUrl')?.value.trim();
    const source = 'admin_capture';
    const severity = document.getElementById('netCaptureSeverity')?.value || 'medium';
    const rawNote = document.getElementById('netCaptureNote')?.value.trim();
    const note = [targetUrl ? `URL: ${targetUrl}` : '', rawNote || ''].filter(Boolean).join('\n') || null;
    if (!content) throw new Error('请先抓取 URL 或粘贴抓包内容');
    const severityEl = document.getElementById('netCaptureSeverityText');
    if (severityEl) severityEl.textContent = severity;
    const data = await ns.api.request('/api/v1/toolbox/capture/analyze', {
      method: 'POST',
      headers: ns.api.headers(),
      body: JSON.stringify({ title: '管理端抓包结果分析', content, severity, source, note }),
    });
    const resultEl = document.getElementById('netCaptureResult');
    if (resultEl) {
      const suggestions = (data.suggestions || []).map((item, idx) => `${idx + 1}. ${item}`).join('\n');
      resultEl.textContent = [
        `分析模式：${data.mode || '-'}`,
        `严重级别：${data.severity || severity}`,
        `摘要：${data.summary || '-'}`,
        suggestions ? `建议：\n${suggestions}` : '',
        '',
        JSON.stringify(data, null, 2),
      ].filter(Boolean).join('\n');
    }
    return data;
  }

  ns.toolbox = { escapeHtml, renderToolTaskTable, renderTaskActions, formatTaskRow, listTasks, updateTask, quickUpdateTask, runNetworkPing, fetchNetworkCapture, analyzeNetworkCapture };
})(window.AegisAdmin);

window.AegisAdmin = window.AegisAdmin || {};

(function (ns) {
  let aiEngineConversationId = null;
  let aiEngineChatPending = false;
  let aiEngineChatHistory = [];

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

  function renderAiExternalKeys(items) {
    const tbody = document.getElementById('aiExternalKeyTbody');
    if (!tbody) return;
    const rows = (items || []).map((item) => {
      const active = item.is_active !== false;
      return `
        <tr>
          <td>${ns.toolbox.escapeHtml(item.id)}</td>
          <td>${ns.toolbox.escapeHtml(item.name || '-')}</td>
          <td>${ns.toolbox.escapeHtml(item.key_prefix || '-')}</td>
          <td>${active ? '启用' : '停用'}</td>
          <td>${ns.toolbox.escapeHtml(item.created_by || '-')}</td>
          <td>${ns.toolbox.escapeHtml(item.last_used_at || '-')}</td>
          <td>
            <button class="table-action-btn" type="button" data-ai-key-action="toggle" data-ai-key-id="${ns.toolbox.escapeHtml(item.id)}" data-ai-key-active="${active ? 'false' : 'true'}">${active ? '停用' : '启用'}</button>
          </td>
        </tr>
      `;
    }).join('');
    tbody.innerHTML = rows || '<tr><td colspan="7">暂无 Key</td></tr>';
  }

  async function listAiExternalKeys() {
    const data = await ns.api.request('/api/v1/admin/ai-external-keys?page=1&size=100', { headers: ns.api.headers() });
    renderAiExternalKeys(data.items || []);
    const result = document.getElementById('aiExternalKeyListResult');
    if (result) result.textContent = `共 ${data.total ?? data.items?.length ?? 0} 条`;
    return data;
  }

  async function createAiExternalKey() {
    const payload = {
      name: document.getElementById('aiExternalKeyName')?.value.trim(),
      remark: document.getElementById('aiExternalKeyRemark')?.value.trim() || null,
    };
    if (!payload.name) throw new Error('请填写 Key 名称');
    const data = await ns.api.request('/api/v1/admin/ai-external-keys', {
      method: 'POST',
      headers: ns.api.headers(),
      body: JSON.stringify(payload),
    });
    const result = document.getElementById('aiExternalKeyCreateResult');
    if (result) {
      result.textContent = [
        'apikey 已生成，请立即保存，后续不会再次展示明文：',
        data.apikey,
        '',
        '调用地址：POST /api/v1/assistant/external/chat',
        '请求体示例：',
        JSON.stringify({ apikey: data.apikey, message: '有哪些系统' }, null, 2),
      ].join('\n');
    }
    await listAiExternalKeys();
    return data;
  }

  async function setAiExternalKeyActive(keyId, isActive) {
    const data = await ns.api.request(`/api/v1/admin/ai-external-keys/${keyId}/active?is_active=${isActive ? 'true' : 'false'}`, {
      method: 'PATCH',
      headers: ns.api.headers(),
    });
    await listAiExternalKeys();
    return data;
  }

  function setValue(id, value) {
    const el = document.getElementById(id);
    if (el) el.value = value ?? '';
  }

  function setChecked(id, value) {
    const el = document.getElementById(id);
    if (el) el.checked = value !== false;
  }

  function fillAiEngineForm(data) {
    setValue('aiEngineType', data.engine_type || 'offline');
    setValue('aiEngineBaseUrl', data.base_url || '');
    setValue('aiEngineModel', data.model || '');
    setValue('aiEngineTimeout', data.timeout_seconds || 120);
    setValue('aiEngineChatPath', data.chat_path || '');
    setValue('aiEngineDiagnosePath', data.diagnose_path || '');
    setValue('aiEngineLogAnalyzePath', data.log_analyze_path || '');
    setValue('aiEngineApiKey', '');
    setChecked('aiEngineEnabled', data.enabled !== false);
  }

  function fillPiGatewayConfig() {
    fillAiEngineForm({
      engine_type: 'pi_gateway',
      base_url: 'http://10.26.234.58:18888',
      model: 'qwen-plus',
      timeout_seconds: 120,
      chat_path: '/v1/messages',
      diagnose_path: '/v1/messages',
      log_analyze_path: '/v1/messages',
      enabled: true,
    });
    const result = document.getElementById('aiEngineConfigResult');
    if (result) result.textContent = '已填入 pi-agent 默认连接信息。API Key 不会自动填入，如需覆盖请手动输入。';
  }

  async function loadAiEngineConfig() {
    const data = await ns.api.request('/api/v1/admin/ai-engine-config', { headers: ns.api.headers() });
    fillAiEngineForm(data);
    const result = document.getElementById('aiEngineConfigResult');
    if (result) {
      result.textContent = JSON.stringify({
        ...data,
        api_key: data.has_api_key ? '已配置，未回显' : '',
      }, null, 2);
    }
    return data;
  }

  async function saveAiEngineConfig() {
    const key = document.getElementById('aiEngineApiKey')?.value.trim() || '';
    const payload = {
      engine_type: document.getElementById('aiEngineType')?.value || 'offline',
      base_url: document.getElementById('aiEngineBaseUrl')?.value.trim() || null,
      api_key: key || null,
      model: document.getElementById('aiEngineModel')?.value.trim() || null,
      timeout_seconds: Number(document.getElementById('aiEngineTimeout')?.value || 120),
      chat_path: document.getElementById('aiEngineChatPath')?.value.trim() || null,
      diagnose_path: document.getElementById('aiEngineDiagnosePath')?.value.trim() || null,
      log_analyze_path: document.getElementById('aiEngineLogAnalyzePath')?.value.trim() || null,
      enabled: document.getElementById('aiEngineEnabled')?.checked !== false,
    };
    const data = await ns.api.request('/api/v1/admin/ai-engine-config', {
      method: 'PUT',
      headers: ns.api.headers(),
      body: JSON.stringify(payload),
    });
    fillAiEngineForm(data);
    const result = document.getElementById('aiEngineConfigResult');
    if (result) result.textContent = JSON.stringify({ saved: true, ...data, api_key: data.has_api_key ? '已配置，未回显' : '' }, null, 2);
    return data;
  }

  function appendAiEngineChatMessage(role, content) {
    const host = document.getElementById('aiEngineChatMessages');
    if (!host) return;
    host.querySelector('.ai-chat-empty')?.remove();
    const message = document.createElement('div');
    message.className = `ai-chat-message ${role}`;
    const label = document.createElement('strong');
    label.textContent = role === 'user' ? '你' : 'AI';
    const body = document.createElement('div');
    body.textContent = content;
    message.append(label, body);
    host.appendChild(message);
    host.scrollTop = host.scrollHeight;
    return body;
  }

  async function readNdjsonStream(path, options, onEvent) {
    const response = await fetch(`${ns.api.base()}${path}`, options);
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.message || data.detail || `HTTP ${response.status}`);
    }
    if (!response.body) throw new Error('浏览器不支持读取流式响应。');
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    while (true) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';
      for (const line of lines) {
        if (!line.trim()) continue;
        const event = JSON.parse(line);
        if (event.type === 'error') throw new Error(event.message || '流式请求失败');
        onEvent(event);
      }
      if (done) break;
    }
    if (buffer.trim()) onEvent(JSON.parse(buffer));
  }

  function setAiEngineChatPending(pending) {
    aiEngineChatPending = pending;
    const button = document.getElementById('btnSendAiEngineChat');
    const input = document.getElementById('aiEngineChatInput');
    if (button) {
      button.disabled = pending;
      button.textContent = pending ? '请求中...' : '发送';
    }
    if (input) input.disabled = pending;
  }

  async function sendAiEngineChat() {
    if (aiEngineChatPending) return;
    const input = document.getElementById('aiEngineChatInput');
    const status = document.getElementById('aiEngineChatStatus');
    const message = input?.value.trim() || '';
    if (!message) {
      if (status) status.textContent = '请输入测试问题。';
      input?.focus();
      return;
    }

    appendAiEngineChatMessage('user', message);
    input.value = '';
    setAiEngineChatPending(true);
    if (status) status.textContent = '正在调用已保存的 AI 引擎配置...';

    try {
      const key = document.getElementById('aiEngineApiKey')?.value.trim() || '';
      let data = null;
      let reply = '';
      const replyBody = appendAiEngineChatMessage('assistant', '');
      await readNdjsonStream('/api/v1/admin/ai-engine-config/test-chat/stream', {
        method: 'POST',
        headers: ns.api.headers(),
        body: JSON.stringify({
          message,
          conversation_id: aiEngineConversationId,
          history: aiEngineChatHistory.slice(-12),
          engine_type: document.getElementById('aiEngineType')?.value || 'offline',
          base_url: document.getElementById('aiEngineBaseUrl')?.value.trim() || null,
          api_key: key || null,
          model: document.getElementById('aiEngineModel')?.value.trim() || null,
          timeout_seconds: Number(document.getElementById('aiEngineTimeout')?.value || 120),
          chat_path: document.getElementById('aiEngineChatPath')?.value.trim() || null,
          diagnose_path: document.getElementById('aiEngineDiagnosePath')?.value.trim() || null,
          log_analyze_path: document.getElementById('aiEngineLogAnalyzePath')?.value.trim() || null,
          enabled: document.getElementById('aiEngineEnabled')?.checked !== false,
        }),
      }, (event) => {
        if (event.type === 'delta') {
          reply += event.text || '';
          if (replyBody) replyBody.textContent = reply;
          if (status) status.textContent = 'AI 正在流式回复...';
        } else if (event.type === 'done') {
          data = event.data || {};
        }
      });
      if (!data) throw new Error('AI 流式响应未正常结束。');
      aiEngineConversationId = data.conversation_id || aiEngineConversationId;
      reply = data.reply || reply || data.summary || '引擎未返回文本内容。';
      aiEngineChatHistory.push({ role: 'user', content: message }, { role: 'assistant', content: reply });
      aiEngineChatHistory = aiEngineChatHistory.slice(-12);
      if (replyBody) replyBody.textContent = reply;
      if (status) {
        const details = [
          `页面引擎：${data.tested_engine_type || '未知'}`,
          `实际模式：${data.mode || '未知'}`,
          `耗时：${data.elapsed_ms ?? '-'} ms`,
        ];
        if (data.fallback_reason) details.push(`降级原因：${data.fallback_reason}`);
        status.textContent = details.join('  |  ');
        status.classList.toggle('warning', Boolean(data.fallback_reason));
      }
    } catch (error) {
      appendAiEngineChatMessage('error', `请求失败：${error.message}`);
      if (status) {
        status.textContent = `测试失败：${error.message}`;
        status.classList.add('warning');
      }
    } finally {
      setAiEngineChatPending(false);
      input?.focus();
    }
  }

  function clearAiEngineChat() {
    aiEngineConversationId = null;
    aiEngineChatHistory = [];
    const host = document.getElementById('aiEngineChatMessages');
    const status = document.getElementById('aiEngineChatStatus');
    if (host) host.innerHTML = '<div class="ai-chat-empty">输入问题以测试 AI 引擎响应。</div>';
    if (status) {
      status.textContent = '已清空会话';
      status.classList.remove('warning');
    }
    document.getElementById('aiEngineChatInput')?.focus();
  }

  document.getElementById('aiExternalKeyTbody')?.addEventListener('click', (event) => {
    const btn = event.target.closest('[data-ai-key-action]');
    if (!btn) return;
    setAiExternalKeyActive(btn.dataset.aiKeyId, btn.dataset.aiKeyActive === 'true').catch((e) => {
      const result = document.getElementById('aiExternalKeyListResult');
      if (result) result.textContent = e.message;
    });
  });

  ns.rulesAudit = {
    buildAuditQuery,
    loadRules,
    saveRules,
    loadAudit,
    listAiExternalKeys,
    createAiExternalKey,
    setAiExternalKeyActive,
    loadAiEngineConfig,
    saveAiEngineConfig,
    fillPiGatewayConfig,
    sendAiEngineChat,
    clearAiEngineChat,
  };
})(window.AegisAdmin);

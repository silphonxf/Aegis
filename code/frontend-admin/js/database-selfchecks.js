window.AegisAdmin = window.AegisAdmin || {};

(function (ns) {
  ns.state = ns.state || {};

  const DB_MARKER = '数据库自检配置';

  function escape(value) {
    return ns.toolbox.escapeHtml(value);
  }

  function value(id) {
    return document.getElementById(id)?.value || '';
  }

  function setValue(id, nextValue) {
    const el = document.getElementById(id);
    if (el) el.value = nextValue ?? '';
  }

  function setText(id, nextValue) {
    const el = document.getElementById(id);
    if (el) el.textContent = nextValue ?? '';
  }

  function envLabel(env) {
    if (env === 'prod') return '生产';
    if (env === 'test') return '测试';
    if (env === 'dev') return '开发';
    return env || '-';
  }

  function frequencyLabel(value) {
    if (value === 'hourly') return '每小时';
    if (value === 'daily') return '每天';
    if (value === 'weekly') return '每周';
    if (value === 'monthly') return '每月';
    return value || '-';
  }

  function extractField(patterns, text) {
    for (const pattern of patterns) {
      const match = text.match(pattern);
      if (match && match[1]) return match[1].trim().replace(/[，,;；。]+$/, '');
    }
    return '';
  }

  function parseSkill(skill, fallbackHost = '') {
    const text = skill || '';
    return {
      db_type: /mariadb/i.test(text) ? 'mariadb' : 'mysql',
      host: extractField([/(?:host|主机|地址|ip)\s*[=:：]\s*([0-9A-Za-z_.-]+)/i], text) || fallbackHost || '',
      port: extractField([/(?:port|端口)\s*[=:：]\s*(\d+)/i], text) || '3306',
      database: extractField([
        /mysql\s*数据库\s*(?:是|为|名为|名称为)?\s*([0-9A-Za-z_$.-]+)\s*(?:用户|用户名|user)/i,
        /(?:database|dbname|db|库名|数据库名|数据库)\s*[=:：]\s*([0-9A-Za-z_$.-]+)/i,
      ], text),
      user: extractField([/(?:用户名|用户|user|username)\s*[=:：]?\s*([^\s，,;；]+)/i], text),
      password: extractField([/(?:密码|口令|password|passwd|pwd)\s*[=:：]?\s*([^\s，,;；]+)/i], text),
      instruction: extractField([/自检要求\s*[=:：]\s*([\s\S]+)/i], text).trim(),
    };
  }

  function isDbSelfcheck(item) {
    const text = `${item.system_code || ''}\n${item.name || ''}\n${item.selfcheck_skill || ''}`.toLowerCase();
    return text.includes(DB_MARKER.toLowerCase()) || /^db[-_]/i.test(item.system_code || '') || text.includes('mysql') || text.includes('mariadb') || text.includes('数据库自检');
  }

  function buildSkill(payload) {
    const dbTypeLabel = payload.db_type === 'mariadb' ? 'MariaDB' : 'MySQL';
    return [
      DB_MARKER,
      `${dbTypeLabel} 数据库自检`,
      `host=${payload.host}`,
      `port=${payload.port || 3306}`,
      `database=${payload.database}`,
      `user=${payload.user}`,
      `password=${payload.password}`,
      '',
      `自检要求: ${payload.instruction || '重点检查连接数、Threads_running、锁等待、死锁、慢 SQL 和异常连接。'}`,
    ].join('\n');
  }

  function collectPayload() {
    const code = value('dbSelfcheckCode').trim();
    const name = value('dbSelfcheckName').trim();
    const host = value('dbSelfcheckHost').trim();
    const database = value('dbSelfcheckDatabase').trim();
    const user = value('dbSelfcheckUser').trim();
    const password = value('dbSelfcheckPassword');
    if (!code || !name || !host || !database || !user || !password) {
      throw new Error('请完整填写编号、名称、主机、数据库名、用户名和密码');
    }
    const port = Number(value('dbSelfcheckPort') || 3306);
    if (!Number.isFinite(port) || port < 1 || port > 65535) throw new Error('端口必须在 1-65535 之间');
    return {
      system_code: code,
      name,
      host_address: host,
      env: value('dbSelfcheckEnv') || 'prod',
      is_active: true,
      check_frequency: value('dbSelfcheckFrequency').trim() || null,
      selfcheck_skill: buildSkill({
        db_type: value('dbSelfcheckType') || 'mysql',
        host,
        port,
        database,
        user,
        password,
        instruction: value('dbSelfcheckInstruction').trim(),
      }),
      log_configs: [],
      owner_user_ids: [],
      remark: value('dbSelfcheckRemark').trim() || null,
    };
  }

  function resetForm() {
    ns.state.editingDbSelfcheckId = null;
    [
      'dbSelfcheckCode',
      'dbSelfcheckName',
      'dbSelfcheckHost',
      'dbSelfcheckDatabase',
      'dbSelfcheckUser',
      'dbSelfcheckPassword',
      'dbSelfcheckInstruction',
      'dbSelfcheckRemark',
    ].forEach((id) => setValue(id, ''));
    setValue('dbSelfcheckType', 'mysql');
    setValue('dbSelfcheckEnv', 'prod');
    setValue('dbSelfcheckPort', '3306');
    setValue('dbSelfcheckFrequency', '');
    setText('dbSelfcheckFormResult', '');
  }

  function showForm(visible) {
    const form = document.getElementById('dbSelfcheckForm');
    if (!form) return;
    form.classList.toggle('hidden', !visible);
  }

  function openCreate() {
    resetForm();
    showForm(true);
    setText('dbSelfcheckFormResult', '新增数据库自检配置');
  }

  function openEdit(id) {
    const item = (ns.state.latestDbSelfchecks || []).find((row) => String(row.id) === String(id));
    if (!item) return;
    const config = parseSkill(item.selfcheck_skill, item.host_address);
    ns.state.editingDbSelfcheckId = item.id;
    setValue('dbSelfcheckCode', item.system_code);
    setValue('dbSelfcheckName', item.name);
    setValue('dbSelfcheckType', config.db_type);
    setValue('dbSelfcheckEnv', item.env || 'prod');
    setValue('dbSelfcheckHost', config.host || item.host_address || '');
    setValue('dbSelfcheckPort', config.port || '3306');
    setValue('dbSelfcheckDatabase', config.database);
    setValue('dbSelfcheckUser', config.user);
    setValue('dbSelfcheckPassword', config.password);
    setValue('dbSelfcheckFrequency', item.check_frequency || '');
    setValue('dbSelfcheckInstruction', config.instruction);
    setValue('dbSelfcheckRemark', item.remark || '');
    showForm(true);
    setText('dbSelfcheckFormResult', `正在编辑 ${item.system_code || item.id}`);
  }

  function cancel() {
    resetForm();
    showForm(false);
  }

  function rowConfig(item) {
    return parseSkill(item.selfcheck_skill, item.host_address);
  }

  function render(items, totalText) {
    const tbody = document.getElementById('dbSelfcheckTbody');
    const summary = document.getElementById('dbSelfcheckSummary');
    ns.state.latestDbSelfchecks = items;
    const rows = items.map((item, idx) => {
      const config = rowConfig(item);
      return `
        <tr>
          <td>${idx + 1}</td>
          <td>${escape(item.system_code || '-')}</td>
          <td>${escape(item.name || '-')}<br /><span class="muted-cell">${escape(envLabel(item.env))}</span></td>
          <td>${escape(config.db_type || 'mysql')}</td>
          <td>${escape(config.host || item.host_address || '-')}:${escape(config.port || '3306')}</td>
          <td>${escape(config.database || '-')}</td>
          <td>${escape(config.user || '-')}</td>
          <td>${escape(frequencyLabel(item.check_frequency))}</td>
          <td>${item.is_active === false ? '停用' : '启用'}</td>
          <td>
            <button class="table-action-btn" type="button" data-db-selfcheck-edit="${escape(item.id)}">编辑</button>
            <button class="table-action-btn" type="button" data-db-selfcheck-toggle="${escape(item.id)}" data-db-selfcheck-active="${item.is_active === false ? 'true' : 'false'}">${item.is_active === false ? '启用' : '停用'}</button>
          </td>
        </tr>
      `;
    }).join('');
    if (summary) summary.textContent = totalText || `匹配 ${items.length} 条`;
    if (tbody) tbody.innerHTML = rows || '<tr><td colspan="10">暂无数据库自检配置</td></tr>';
  }

  async function list() {
    const params = new URLSearchParams({ page: '1', size: '100', sort_by: 'updated_at', sort_order: 'desc' });
    const active = value('dbSelfcheckActive');
    if (active) params.set('is_active', active);
    const data = await ns.api.request(`/api/v1/admin/systems?${params.toString()}`, { headers: ns.api.headers() });
    const keyword = value('dbSelfcheckKeyword').trim().toLowerCase();
    const items = (data.items || [])
      .filter(isDbSelfcheck)
      .filter((item) => {
        if (!keyword) return true;
        const config = rowConfig(item);
        return [
          item.system_code,
          item.name,
          item.host_address,
          config.host,
          config.database,
          config.user,
        ].join(' ').toLowerCase().includes(keyword);
      });
    render(items, `匹配 ${items.length} 条`);
    return items;
  }

  async function save() {
    const payload = collectPayload();
    const id = ns.state.editingDbSelfcheckId;
    const data = await ns.api.request(id ? `/api/v1/admin/systems/${id}` : '/api/v1/admin/systems', {
      method: id ? 'PUT' : 'POST',
      headers: ns.api.headers(),
      body: JSON.stringify(payload),
    });
    setText('dbSelfcheckFormResult', '保存成功');
    resetForm();
    showForm(false);
    await list();
    return data;
  }

  async function toggle(id, isActive) {
    const data = await ns.api.request(`/api/v1/admin/systems/${id}/active?is_active=${isActive ? 'true' : 'false'}`, {
      method: 'PATCH',
      headers: ns.api.headers(),
    });
    await list();
    return data;
  }

  document.getElementById('dbSelfcheckTbody')?.addEventListener('click', (event) => {
    const editBtn = event.target.closest('[data-db-selfcheck-edit]');
    const toggleBtn = event.target.closest('[data-db-selfcheck-toggle]');
    if (editBtn) openEdit(editBtn.dataset.dbSelfcheckEdit);
    if (toggleBtn) {
      toggle(toggleBtn.dataset.dbSelfcheckToggle, toggleBtn.dataset.dbSelfcheckActive === 'true').catch((e) => {
        setText('dbSelfcheckSummary', e.message);
      });
    }
  });

  document.getElementById('dbSelfcheckForm')?.addEventListener('submit', (event) => {
    event.preventDefault();
    save().catch((e) => {
      setText('dbSelfcheckFormResult', e.message);
    });
  });

  ns.databaseSelfchecks = { list, openCreate, openEdit, cancel, save, toggle };
})(window.AegisAdmin);

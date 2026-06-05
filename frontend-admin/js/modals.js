window.AegisAdmin = window.AegisAdmin || {};

(function (ns) {
  function openModal(id) {
    if (!ns.state.token) {
      ns.auth?.forceRelogin?.('请先登录后继续操作');
      return;
    }
    const modal = document.getElementById(id);
    modal?.classList.remove('hidden');
    modal?.removeAttribute('hidden');
    modal?.setAttribute('aria-hidden', 'false');
  }

  function closeModal(id) {
    const modal = document.getElementById(id);
    modal?.classList.add('hidden');
    modal?.setAttribute('hidden', '');
    modal?.setAttribute('aria-hidden', 'true');
  }

  function parseOwnerIds() {
    return (document.getElementById('modalSystemOwnerIds').value || '')
      .split(',')
      .map((v) => Number(v.trim()))
      .filter((v) => Number.isFinite(v) && v > 0);
  }

  function setSystemOwnerIds(ownerIds) {
    const ids = Array.from(new Set((ownerIds || []).map(Number).filter((v) => Number.isFinite(v) && v > 0)));
    setValue('modalSystemOwnerIds', ids.join(','));
    renderSystemOwnerSummary();
  }

  function roleLabel(roleCode) {
    if (roleCode === 'super_admin') return '超级管理员';
    if (roleCode === 'admin') return '管理员';
    return '巡检员';
  }

  function renderSystemOwnerSummary() {
    const host = document.getElementById('modalSystemOwnerSummary');
    if (!host) return;
    const ids = parseOwnerIds();
    if (!ids.length) {
      host.textContent = '暂未选择管理员';
      return;
    }
    const userMap = new Map((ns.state.latestUsers || []).map((u) => [Number(u.id), u]));
    host.textContent = ids.map((id) => {
      const user = userMap.get(Number(id));
      return user ? `${user.username}（ID:${id}）` : `用户ID:${id}`;
    }).join('，');
  }

  async function ensureLatestUsers() {
    if (Array.isArray(ns.state.latestUsers) && ns.state.latestUsers.length) return ns.state.latestUsers;
    const d = await ns.api.request('/api/v1/admin/users?page=1&size=200', { headers: ns.api.headers() });
    ns.state.latestUsers = Array.isArray(d.items) ? d.items : [];
    return ns.state.latestUsers;
  }

  function resetCreateUserModal() {
    const ids = ['modalUserName', 'modalUserPassword'];
    ids.forEach((id) => { const el = document.getElementById(id); if (el) el.value = ''; });
  }

  function resetCreateSystemModal() {
    ns.state.editingSystemId = null;
    const ids = [
      'modalSystemCode',
      'modalSystemName',
      'modalSystemHostAddress',
      'modalSystemOwnerIds',
      'modalSystemCheckFrequency',
      'modalSystemLogConfigs',
      'modalSystemSelfcheckSkill',
      'modalSystemRemark',
      'modalSystemActive',
    ];
    ids.forEach((id) => { const el = document.getElementById(id); if (el) el.value = ''; });
    const env = document.getElementById('modalSystemEnv');
    if (env) env.value = 'prod';
    const active = document.getElementById('modalSystemActive');
    if (active) active.value = 'true';
    const frequency = document.getElementById('modalSystemCheckFrequency');
    if (frequency) frequency.value = '';
    const testResult = document.getElementById('systemHostTestResult');
    if (testResult) testResult.textContent = '';
    const title = document.getElementById('systemModalTitle');
    const submit = document.getElementById('btnSubmitCreateSystem');
    const deleteBtn = document.getElementById('btnDeleteSystem');
    if (title) title.textContent = '新增系统';
    if (submit) submit.textContent = '确认新增';
    if (deleteBtn) deleteBtn.classList.add('hidden');
    renderSystemOwnerSummary();
  }

  function resetCreateAssetModal() {
    ns.state.editingAssetId = null;
    const defaults = {
      modalAssetName: '',
      modalAssetQrContent: '',
      modalAssetNfcTag: '',
      modalAssetCheckItems: '',
      modalAssetRemark: '',
      modalAssetActive: 'true',
    };
    Object.entries(defaults).forEach(([id, value]) => {
      const el = document.getElementById(id);
      if (el) el.value = value;
    });
    const title = document.getElementById('assetModalTitle');
    const submit = document.getElementById('btnSubmitCreateAsset');
    const deleteBtn = document.getElementById('btnDeleteAsset');
    if (title) title.textContent = '新增机房';
    if (submit) submit.textContent = '确认新增';
    if (deleteBtn) deleteBtn.classList.add('hidden');
  }

  function openCreateAssetModal() {
    resetCreateAssetModal();
    openModal('createAssetModal');
  }

  function setValue(id, value) {
    const el = document.getElementById(id);
    if (el) el.value = value ?? '';
  }

  function openCreateSystemModal() {
    resetCreateSystemModal();
    ensureLatestUsers().then(renderSystemOwnerSummary).catch(() => {});
    openModal('createSystemModal');
  }

  function openEditSystemModal(item) {
    ns.state.editingSystemId = item.id;
    const title = document.getElementById('systemModalTitle');
    const submit = document.getElementById('btnSubmitCreateSystem');
    const deleteBtn = document.getElementById('btnDeleteSystem');
    if (title) title.textContent = '编辑系统';
    if (submit) submit.textContent = '保存修改';
    if (deleteBtn) deleteBtn.classList.remove('hidden');
    setValue('modalSystemCode', item.system_code);
    setValue('modalSystemName', item.name);
    setValue('modalSystemHostAddress', item.host_address);
    setValue('modalSystemEnv', item.env || 'prod');
    setValue('modalSystemActive', item.is_active === false ? 'false' : 'true');
    setSystemOwnerIds(Array.isArray(item.owner_user_ids) ? item.owner_user_ids : []);
    setValue('modalSystemCheckFrequency', item.check_frequency);
    setValue('modalSystemRemark', item.remark);
    setValue('modalSystemSelfcheckSkill', item.selfcheck_skill);
    const logPaths = Array.isArray(item.log_configs)
      ? item.log_configs.map((cfg) => cfg.absolute_path || '').filter(Boolean).join('\n')
      : '';
    setValue('modalSystemLogConfigs', logPaths);
    ensureLatestUsers().then(renderSystemOwnerSummary).catch(() => {});
    openModal('createSystemModal');
  }

  async function testSystemHost() {
    const host = document.getElementById('modalSystemHostAddress')?.value.trim();
    const result = document.getElementById('systemHostTestResult');
    if (!host) {
      if (result) result.textContent = '请先输入系统地址/IP';
      return false;
    }
    if (result) result.textContent = '检测中...';
    const data = await ns.api.request('/api/v1/toolbox/ping', {
      method: 'POST',
      headers: ns.api.headers(),
      body: JSON.stringify({ host, count: 1 }),
    });
    if (result) result.textContent = data.ok ? `可通（${data.latency_ms}ms）` : '不可通';
    return Boolean(data.ok);
  }

  async function openSystemOwnerPicker() {
    await ensureLatestUsers();
    renderSystemOwnerPicker();
    openModal('systemOwnerPickerModal');
  }

  function renderSystemOwnerPicker(keyword = '') {
    const host = document.getElementById('systemOwnerPickerList');
    if (!host) return;
    const selected = new Set(parseOwnerIds().map(String));
    const q = keyword.trim().toLowerCase();
    const users = (ns.state.latestUsers || []).filter((u) => {
      if (!q) return true;
      return `${u.username || ''} ${u.id || ''}`.toLowerCase().includes(q);
    });
    host.innerHTML = users.map((u) => `
      <label class="picker-row">
        <input type="checkbox" value="${ns.toolbox.escapeHtml(u.id)}" ${selected.has(String(u.id)) ? 'checked' : ''} />
        <div>
          <strong>${ns.toolbox.escapeHtml(u.username || '-')}</strong>
          <span>ID:${ns.toolbox.escapeHtml(u.id)} / ${roleLabel(u.role_code || u.role)}</span>
        </div>
      </label>
    `).join('') || '<div class="selection-summary">暂无匹配用户</div>';
  }

  function confirmSystemOwners() {
    const ids = Array.from(document.querySelectorAll('#systemOwnerPickerList input[type="checkbox"]:checked'))
      .map((input) => Number(input.value))
      .filter((v) => Number.isFinite(v) && v > 0);
    setSystemOwnerIds(ids);
    closeModal('systemOwnerPickerModal');
  }

  function openEditAssetModal(item) {
    ns.state.editingAssetId = item.id;
    const title = document.getElementById('assetModalTitle');
    const submit = document.getElementById('btnSubmitCreateAsset');
    const deleteBtn = document.getElementById('btnDeleteAsset');
    if (title) title.textContent = '编辑机房';
    if (submit) submit.textContent = '保存修改';
    if (deleteBtn) deleteBtn.classList.remove('hidden');
    setValue('modalAssetName', item.room_name);
    setValue('modalAssetQrContent', item.qr_content);
    setValue('modalAssetNfcTag', item.nfc_tag);
    setValue('modalAssetCheckItems', (item.check_items || []).join('\n'));
    setValue('modalAssetRemark', item.remark);
    setValue('modalAssetActive', item.is_active === false ? 'false' : 'true');
    openModal('createAssetModal');
  }

  async function submitCreateUser() {
    const d = await ns.api.request('/api/v1/admin/users', {
      method: 'POST',
      headers: ns.api.headers(),
      body: JSON.stringify({
        username: document.getElementById('modalUserName').value.trim(),
        password: document.getElementById('modalUserPassword').value,
        role_code: document.getElementById('modalUserRole').value,
      }),
    });
    ns.users.renderUserResultBoard([d], '新增成功，已创建 1 个用户');
    closeModal('createUserModal');
    resetCreateUserModal();
    return d;
  }

  async function submitCreateSystem() {
    const ownerIds = parseOwnerIds();
    const hostAddress = document.getElementById('modalSystemHostAddress').value.trim();
    if (!hostAddress) {
      throw new Error('请先填写系统地址/IP');
    }
    if (hostAddress && !(await testSystemHost())) {
      throw new Error('系统地址/IP 不可通，已阻止保存');
    }
    const logConfigs = (document.getElementById('modalSystemLogConfigs').value || '')
      .split('\n')
      .map((v) => v.trim())
      .filter(Boolean)
      .map((absolutePath) => ({
        log_name: absolutePath.split('/').filter(Boolean).at(-1) || absolutePath,
        absolute_path: absolutePath,
        is_active: true,
      }));
    const payload = {
      system_code: document.getElementById('modalSystemCode').value.trim(),
      name: document.getElementById('modalSystemName').value.trim(),
      host_address: hostAddress || null,
      env: document.getElementById('modalSystemEnv').value || 'prod',
      is_active: document.getElementById('modalSystemActive')?.value !== 'false',
      owner_user_ids: ownerIds,
      check_frequency: document.getElementById('modalSystemCheckFrequency').value.trim() || null,
      selfcheck_skill: document.getElementById('modalSystemSelfcheckSkill')?.value.trim() || null,
      log_configs: logConfigs,
      remark: document.getElementById('modalSystemRemark').value.trim() || null,
    };
    const d = await ns.api.request(ns.state.editingSystemId ? `/api/v1/admin/systems/${ns.state.editingSystemId}` : '/api/v1/admin/systems', {
      method: ns.state.editingSystemId ? 'PUT' : 'POST',
      headers: ns.api.headers(),
      body: JSON.stringify(payload),
    });
    await ns.systems.findSystems();
    closeModal('createSystemModal');
    resetCreateSystemModal();
    return d;
  }

  async function submitCreateAsset() {
    const payload = {
      room_name: document.getElementById('modalAssetName').value.trim(),
      qr_content: document.getElementById('modalAssetQrContent').value.trim(),
      nfc_tag: document.getElementById('modalAssetNfcTag').value.trim() || null,
      check_items: (document.getElementById('modalAssetCheckItems').value || '')
        .split('\n')
        .map((item) => item.trim())
        .filter(Boolean),
      remark: document.getElementById('modalAssetRemark').value.trim() || null,
      is_active: document.getElementById('modalAssetActive')?.value !== 'false',
    };
    const d = ns.state.editingAssetId
      ? await ns.assets.updateAsset(ns.state.editingAssetId, payload)
      : await ns.assets.createAsset(payload);
    closeModal('createAssetModal');
    resetCreateAssetModal();
    return d;
  }

  async function deleteEditingSystem() {
    if (!ns.state.editingSystemId) return null;
    const d = await ns.systems.deleteSystem(ns.state.editingSystemId);
    closeModal('createSystemModal');
    resetCreateSystemModal();
    return d;
  }

  async function deleteEditingAsset() {
    if (!ns.state.editingAssetId) return null;
    const d = await ns.assets.retireAsset(ns.state.editingAssetId);
    closeModal('createAssetModal');
    resetCreateAssetModal();
    return d;
  }

  ns.modals = {
    openModal,
    closeModal,
    openCreateSystemModal,
    openEditSystemModal,
    openSystemOwnerPicker,
    renderSystemOwnerPicker,
    confirmSystemOwners,
    testSystemHost,
    openCreateAssetModal,
    openEditAssetModal,
    submitCreateUser,
    submitCreateSystem,
    submitCreateAsset,
    deleteEditingSystem,
    deleteEditingAsset,
    resetCreateUserModal,
    resetCreateSystemModal,
    resetCreateAssetModal,
  };
})(window.AegisAdmin);

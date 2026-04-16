window.AegisAdmin = window.AegisAdmin || {};

(function (ns) {
  function openModal(id) {
    document.getElementById(id)?.classList.remove('hidden');
  }

  function closeModal(id) {
    document.getElementById(id)?.classList.add('hidden');
  }

  function resetCreateUserModal() {
    const ids = ['modalUserName', 'modalUserPassword'];
    ids.forEach((id) => { const el = document.getElementById(id); if (el) el.value = ''; });
  }

  function resetCreateSystemModal() {
    const ids = ['modalSystemCode', 'modalSystemName'];
    ids.forEach((id) => { const el = document.getElementById(id); if (el) el.value = ''; });
  }

  function resetCreateAssetModal() {
    const defaults = {
      modalAssetCode: '',
      modalAssetName: '',
      modalAssetCategory: 'server',
      modalAssetSystemId: '',
      modalAssetLocation: '',
      modalAssetStatus: 'in_use',
    };
    Object.entries(defaults).forEach(([id, value]) => {
      const el = document.getElementById(id);
      if (el) el.value = value;
    });
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
    const d = await ns.api.request('/api/v1/admin/systems', {
      method: 'POST',
      headers: ns.api.headers(),
      body: JSON.stringify({
        system_code: document.getElementById('modalSystemCode').value.trim(),
        name: document.getElementById('modalSystemName').value.trim(),
        env: document.getElementById('modalSystemEnv').value || 'prod',
      }),
    });
    ns.systems.renderSystemResultBoard([d], '新增成功，已创建 1 个系统');
    closeModal('createSystemModal');
    resetCreateSystemModal();
    return d;
  }

  async function submitCreateAsset() {
    const payload = {
      asset_code: document.getElementById('modalAssetCode').value.trim(),
      name: document.getElementById('modalAssetName').value.trim(),
      category: document.getElementById('modalAssetCategory').value.trim() || 'server',
      system_id: document.getElementById('modalAssetSystemId').value.trim() ? Number(document.getElementById('modalAssetSystemId').value) : null,
      location: document.getElementById('modalAssetLocation').value.trim() || null,
      status: document.getElementById('modalAssetStatus').value.trim() || 'in_use',
    };
    const d = await ns.assets.createAsset(payload);
    closeModal('createAssetModal');
    resetCreateAssetModal();
    return d;
  }

  ns.modals = {
    openModal,
    closeModal,
    submitCreateUser,
    submitCreateSystem,
    submitCreateAsset,
    resetCreateUserModal,
    resetCreateSystemModal,
    resetCreateAssetModal,
  };
})(window.AegisAdmin);

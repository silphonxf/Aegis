window.AegisAdmin = window.AegisAdmin || {};

(function (ns) {
  ns.state = ns.state || {};

  function escape(value) {
    return ns.toolbox.escapeHtml(value ?? '');
  }

  function setValue(id, value) {
    const el = document.getElementById(id);
    if (el) el.value = value ?? '';
  }

  function setModalMode(item = null) {
    ns.state.editingPointId = item?.id || null;
    const title = document.getElementById('pointModalTitle');
    const submit = document.getElementById('btnSubmitPoint');
    const deleteBtn = document.getElementById('btnDeletePoint');
    if (title) title.textContent = item ? '编辑巡检点' : '新增巡检点';
    if (submit) submit.textContent = item ? '保存修改' : '确认新增';
    if (deleteBtn) deleteBtn.classList.toggle('hidden', !item);
  }

  async function hydratePointSelectors() {
    const [rooms, systems] = await Promise.all([
      ns.api.loadOptions('/api/v1/admin/rooms?include_inactive=true&page=1&size=500'),
      ns.api.loadOptions('/api/v1/admin/systems?page=1&size=200'),
    ]).catch(() => [[], []]);

    const roomOptions = ['<option value="">不绑定机房</option>']
      .concat(rooms.map((item) => `<option value="${escape(item.id)}">${escape(item.room_code || item.id)} / ${escape(item.room_name || '-')}</option>`));
    const systemOptions = ['<option value="">不绑定系统</option>']
      .concat(systems.map((item) => `<option value="${escape(item.id)}">${escape(item.system_code || item.id)} / ${escape(item.name || '-')}</option>`));

    const roomEl = document.getElementById('modalPointRoomId');
    const systemEl = document.getElementById('modalPointSystemId');
    if (roomEl) roomEl.innerHTML = roomOptions.join('');
    if (systemEl) systemEl.innerHTML = systemOptions.join('');
  }

  function resetPointModal() {
    setModalMode(null);
    [
      'modalPointCode',
      'modalPointName',
      'modalPointQrContent',
      'modalPointNfcTag',
      'modalPointLocationDetail',
    ].forEach((id) => setValue(id, ''));
    setValue('modalPointType', 'room');
    setValue('modalPointRoomId', '');
    setValue('modalPointSystemId', '');
    setValue('modalPointActive', 'true');
  }

  async function openCreatePointModal() {
    resetPointModal();
    await hydratePointSelectors();
    ns.modals.openModal('createPointModal');
  }

  async function openEditPointModal(item) {
    await hydratePointSelectors();
    setModalMode(item);
    setValue('modalPointCode', item.point_code);
    setValue('modalPointName', item.point_name);
    setValue('modalPointType', item.point_type || 'room');
    setValue('modalPointRoomId', item.room_id);
    setValue('modalPointSystemId', item.system_id);
    setValue('modalPointQrContent', item.qr_content);
    setValue('modalPointNfcTag', item.nfc_tag);
    setValue('modalPointLocationDetail', item.location_detail);
    setValue('modalPointActive', item.is_active === false ? 'false' : 'true');
    ns.modals.openModal('createPointModal');
  }

  function pointPayload() {
    const pointCode = document.getElementById('modalPointCode')?.value.trim();
    return {
      point_code: pointCode,
      point_name: document.getElementById('modalPointName')?.value.trim(),
      point_type: document.getElementById('modalPointType')?.value || 'room',
      room_id: Number(document.getElementById('modalPointRoomId')?.value || 0) || null,
      system_id: Number(document.getElementById('modalPointSystemId')?.value || 0) || null,
      qr_content: document.getElementById('modalPointQrContent')?.value.trim() || pointCode,
      nfc_tag: document.getElementById('modalPointNfcTag')?.value.trim() || null,
      location_detail: document.getElementById('modalPointLocationDetail')?.value.trim() || null,
      is_active: document.getElementById('modalPointActive')?.value !== 'false',
    };
  }

  function filteredPoints(items) {
    const keyword = document.getElementById('pointFilterKeyword')?.value.trim().toLowerCase() || '';
    const active = document.getElementById('pointFilterActive')?.value;
    return (items || []).filter((item) => {
      if (active && String(item.is_active) !== active) return false;
      if (!keyword) return true;
      return [item.point_code, item.point_name, item.point_type, item.qr_content, item.nfc_tag, item.location_detail]
        .some((value) => String(value || '').toLowerCase().includes(keyword));
    });
  }

  function renderPoints(items) {
    const tbody = document.getElementById('pointListTbody');
    const rows = (items || []).map((item, idx) => `
      <tr>
        <td>${idx + 1}</td>
        <td>${escape(item.point_code || '-')}</td>
        <td>${escape(item.point_name || '-')}</td>
        <td>${escape(item.point_type || '-')}</td>
        <td>${escape(item.room_id ?? '-')}</td>
        <td>${escape(item.system_id ?? '-')}</td>
        <td>${escape(item.qr_content || '-')}</td>
        <td>${escape(item.nfc_tag || '-')}</td>
        <td>${escape(item.location_detail || '-')}</td>
        <td>${item.is_active === false ? '停用' : '启用'}</td>
        <td>
          <button class="table-action-btn" type="button" data-point-action="edit" data-point-id="${escape(item.id)}">编辑</button>
          <button class="table-action-btn danger" type="button" data-point-action="delete" data-point-id="${escape(item.id)}">停用</button>
        </td>
      </tr>
    `).join('');
    if (tbody) tbody.innerHTML = rows || '<tr><td colspan="11">暂无巡检点数据</td></tr>';
  }

  async function listInspectionPoints() {
    const data = await ns.api.request('/api/v1/admin/inspection-points', { headers: ns.api.headers() });
    ns.state.latestInspectionPoints = Array.isArray(data.items) ? data.items : [];
    const items = filteredPoints(ns.state.latestInspectionPoints);
    renderPoints(items);
    const summary = document.getElementById('pointListSummary');
    if (summary) summary.textContent = `匹配 ${items.length} 条，共 ${ns.state.latestInspectionPoints.length} 条巡检点`;
    const raw = document.getElementById('pointListResult');
    if (raw) raw.textContent = JSON.stringify(data, null, 2);
    return data;
  }

  function findPoint(pointId) {
    return (ns.state.latestInspectionPoints || []).find((item) => String(item.id) === String(pointId));
  }

  async function submitPoint() {
    const editingId = ns.state.editingPointId;
    const data = await ns.api.request(editingId ? `/api/v1/admin/inspection-points/${editingId}` : '/api/v1/admin/inspection-points', {
      method: editingId ? 'PUT' : 'POST',
      headers: ns.api.headers(),
      body: JSON.stringify(pointPayload()),
    });
    ns.modals.closeModal('createPointModal');
    resetPointModal();
    await listInspectionPoints();
    return data;
  }

  async function deletePoint(pointId = ns.state.editingPointId) {
    if (!pointId) return null;
    if (!window.confirm('确认停用该巡检点？数据会保留用于历史追溯。')) return null;
    const data = await ns.api.request(`/api/v1/admin/inspection-points/${pointId}`, {
      method: 'DELETE',
      headers: ns.api.headers(),
    });
    ns.modals.closeModal('createPointModal');
    resetPointModal();
    await listInspectionPoints();
    return data;
  }

  document.getElementById('pointListTbody')?.addEventListener('click', (event) => {
    const btn = event.target.closest('[data-point-action]');
    if (!btn) return;
    const pointId = btn.dataset.pointId;
    if (btn.dataset.pointAction === 'edit') {
      const point = findPoint(pointId);
      if (point) openEditPointModal(point).catch((e) => {
        const el = document.getElementById('pointListSummary');
        if (el) el.textContent = e.message;
      });
    }
    if (btn.dataset.pointAction === 'delete') {
      deletePoint(pointId).catch((e) => {
        const el = document.getElementById('pointListSummary');
        if (el) el.textContent = e.message;
      });
    }
  });

  ns.inspectionPoints = {
    hydratePointSelectors,
    listInspectionPoints,
    openCreatePointModal,
    openEditPointModal,
    submitPoint,
    deletePoint,
    resetPointModal,
  };
})(window.AegisAdmin);

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
      ns.api.loadOptions('/api/v1/admin/rooms?include_inactive=false&size=200'),
      ns.api.loadOptions('/api/v1/admin/systems?is_active=true&size=200&sort_by=name&sort_order=asc'),
    ]);
    ns.state.latestRooms = rooms;
    ns.state.latestPointSystems = systems;

    const roomEl = document.getElementById('modalPointRoomId');
    if (roomEl) {
      roomEl.innerHTML = [
        '<option value="">请选择机房</option>',
        ...rooms.map((item) => `<option value="${escape(item.id)}">${escape(item.room_name || item.room_code || item.id)}</option>`),
      ].join('');
    }

    const systemEl = document.getElementById('modalPointSystemId');
    if (systemEl) {
      systemEl.innerHTML = [
        '<option value="">不绑定系统</option>',
        ...systems.map((item) => `<option value="${escape(item.id)}">${escape(item.name || item.system_code || item.id)}</option>`),
      ].join('');
    }
    return { rooms, systems };
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
    setValue('modalPointType', 'point');
    setValue('modalPointRoomId', '');
    setValue('modalPointSystemId', '');
    setValue('modalPointActive', 'true');
  }

  async function openCreatePointModal() {
    await hydratePointSelectors();
    resetPointModal();
    ns.modals.openModal('createPointModal');
  }

  async function openEditPointModal(item) {
    await hydratePointSelectors();
    setModalMode(item);
    setValue('modalPointCode', item.point_code);
    setValue('modalPointName', item.point_name);
    setValue('modalPointType', item.point_type || 'point');
    setValue('modalPointRoomId', item.room_id || '');
    setValue('modalPointSystemId', item.system_id || '');
    setValue('modalPointQrContent', item.qr_content);
    setValue('modalPointNfcTag', item.nfc_tag);
    setValue('modalPointLocationDetail', item.location_detail);
    setValue('modalPointActive', item.is_active === false ? 'false' : 'true');
    ns.modals.openModal('createPointModal');
  }

  function pointPayload() {
    const pointCode = document.getElementById('modalPointCode')?.value.trim();
    const roomId = document.getElementById('modalPointRoomId')?.value;
    const systemId = document.getElementById('modalPointSystemId')?.value;
    return {
      point_code: pointCode,
      point_name: document.getElementById('modalPointName')?.value.trim(),
      point_type: document.getElementById('modalPointType')?.value || 'point',
      room_id: roomId ? Number(roomId) : null,
      system_id: systemId ? Number(systemId) : null,
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
    const rows = (items || []).map((item, idx) => {
      const isActive = item.is_active !== false;
      const toggleLabel = isActive ? '停用' : '启用';
      const dangerClass = isActive ? ' danger' : '';
      return `
        <tr>
          <td>${idx + 1}</td>
          <td>${escape(item.point_code || '-')}</td>
          <td>${escape(item.point_name || '-')}</td>
          <td>${escape(item.point_type || '-')}</td>
          <td>${escape(item.room_name || item.room_id || '-')}</td>
          <td>${escape(item.system_name || item.system_id || '-')}</td>
          <td>${escape(item.qr_content || '-')}</td>
          <td>${escape(item.nfc_tag || '-')}</td>
          <td>${escape(item.location_detail || '-')}</td>
          <td>${isActive ? '启用' : '停用'}</td>
          <td>
            <button class="table-action-btn" type="button" data-point-action="edit" data-point-id="${escape(item.id)}">编辑</button>
            <button class="table-action-btn${dangerClass}" type="button" data-point-action="toggle" data-point-active="${isActive ? 'false' : 'true'}" data-point-id="${escape(item.id)}">${toggleLabel}</button>
          </td>
        </tr>
      `;
    }).join('');
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
    if (!document.getElementById('modalPointRoomId')?.value) {
      throw new Error('请选择所属机房');
    }
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
    const data = await setPointActive(pointId, false);
    ns.modals.closeModal('createPointModal');
    resetPointModal();
    return data;
  }

  async function setPointActive(pointId, isActive) {
    const label = isActive ? '启用' : '停用';
    const data = await ns.api.request(`/api/v1/admin/inspection-points/${pointId}/active?is_active=${isActive ? 'true' : 'false'}`, {
      method: 'PATCH',
      headers: ns.api.headers(),
    });
    const summary = document.getElementById('pointListSummary');
    if (summary) summary.textContent = `${label}巡检点成功`;
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
    if (btn.dataset.pointAction === 'toggle') {
      const nextActive = btn.dataset.pointActive === 'true';
      const label = nextActive ? '启用' : '停用';
      if (!window.confirm(`确认${label}该巡检点？`)) return;
      setPointActive(pointId, nextActive).catch((e) => {
        const el = document.getElementById('pointListSummary');
        if (el) el.textContent = e.message;
      });
    }
  });

  ns.inspectionPoints = {
    listInspectionPoints,
    openCreatePointModal,
    openEditPointModal,
    hydratePointSelectors,
    submitPoint,
    deletePoint,
    setPointActive,
    resetPointModal,
  };
})(window.AegisAdmin);

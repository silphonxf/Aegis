window.AegisAdmin = window.AegisAdmin || {};

(function (ns) {
  ns.state = ns.state || {};

  function escape(value) {
    return ns.toolbox.escapeHtml(value ?? '');
  }

  function value(id) {
    return document.getElementById(id)?.value ?? '';
  }

  function setValue(id, nextValue) {
    const el = document.getElementById(id);
    if (el) el.value = nextValue ?? '';
  }

  function checkItemsFromText(text) {
    return String(text || '')
      .split(/\r?\n/)
      .map((item) => item.trim())
      .filter(Boolean);
  }

  function setModalMode(item = null) {
    ns.state.editingRoomId = item?.id || null;
    const title = document.getElementById('roomModalTitle');
    const submit = document.getElementById('btnSubmitRoom');
    const deleteBtn = document.getElementById('btnDeleteRoom');
    if (title) title.textContent = item ? '编辑机房' : '新增机房';
    if (submit) submit.textContent = item ? '保存修改' : '确认新增';
    if (deleteBtn) deleteBtn.classList.toggle('hidden', !item || item.is_active === false);
  }

  function resetRoomModal() {
    setModalMode(null);
    [
      'modalRoomCode',
      'modalRoomName',
      'modalRoomQrContent',
      'modalRoomNfcTag',
      'modalRoomCheckItems',
      'modalRoomLocationDetail',
      'modalRoomRemark',
    ].forEach((id) => setValue(id, ''));
    setValue('modalRoomWeekdayCount', '1');
    setValue('modalRoomHolidayCount', '1');
    setValue('modalRoomActive', 'true');
  }

  function openCreateRoomModal() {
    resetRoomModal();
    ns.modals.openModal('createRoomModal');
  }

  function openEditRoomModal(item) {
    setModalMode(item);
    setValue('modalRoomCode', item.room_code || '');
    setValue('modalRoomName', item.room_name || '');
    setValue('modalRoomQrContent', item.qr_content || '');
    setValue('modalRoomNfcTag', item.nfc_tag || '');
    setValue('modalRoomWeekdayCount', item.weekday_inspection_count ?? 1);
    setValue('modalRoomHolidayCount', item.holiday_inspection_count ?? 1);
    setValue('modalRoomCheckItems', Array.isArray(item.check_items) ? item.check_items.join('\n') : '');
    setValue('modalRoomLocationDetail', item.location_detail || '');
    setValue('modalRoomRemark', item.remark || '');
    setValue('modalRoomActive', item.is_active === false ? 'false' : 'true');
    ns.modals.openModal('createRoomModal');
  }

  function roomPayload() {
    return {
      room_code: value('modalRoomCode').trim() || null,
      room_name: value('modalRoomName').trim(),
      qr_content: value('modalRoomQrContent').trim(),
      nfc_tag: value('modalRoomNfcTag').trim() || null,
      weekday_inspection_count: Number(value('modalRoomWeekdayCount') || 0),
      holiday_inspection_count: Number(value('modalRoomHolidayCount') || 0),
      check_items: checkItemsFromText(value('modalRoomCheckItems')),
      location_detail: value('modalRoomLocationDetail').trim() || null,
      remark: value('modalRoomRemark').trim() || null,
      is_active: value('modalRoomActive') !== 'false',
    };
  }

  function filteredRooms(items) {
    const keyword = value('roomFilterKeyword').trim().toLowerCase();
    return (items || []).filter((item) => {
      if (!keyword) return true;
      return [item.room_code, item.room_name, item.qr_content, item.nfc_tag, item.location_detail]
        .some((field) => String(field || '').toLowerCase().includes(keyword));
    });
  }

  function renderRooms(items) {
    const tbody = document.getElementById('roomListTbody');
    const rows = (items || []).map((item, idx) => {
      const isActive = item.is_active !== false;
      return `
        <tr>
          <td>${idx + 1}</td>
          <td>${escape(item.room_code || '-')}</td>
          <td>${escape(item.room_name || '-')}</td>
          <td>${escape(item.qr_content || '-')}</td>
          <td>${escape(item.nfc_tag || '-')}</td>
          <td>${escape(item.weekday_inspection_count ?? 1)}</td>
          <td>${escape(item.holiday_inspection_count ?? 1)}</td>
          <td>${escape((item.check_items || []).join(' / ') || '-')}</td>
          <td>${isActive ? '启用' : '停用'}</td>
          <td>
            <button class="table-action-btn" type="button" data-room-action="edit" data-room-id="${escape(item.id)}">编辑</button>
            <button class="table-action-btn${isActive ? ' danger' : ''}" type="button" data-room-action="toggle" data-room-active="${isActive ? 'false' : 'true'}" data-room-id="${escape(item.id)}">${isActive ? '停用' : '启用'}</button>
          </td>
        </tr>
      `;
    }).join('');
    if (tbody) tbody.innerHTML = rows || '<tr><td colspan="10">暂无机房数据</td></tr>';
  }

  async function listRooms() {
    const includeInactive = value('roomFilterActive') === 'all';
    const data = await ns.api.request(`/api/v1/admin/rooms?include_inactive=${includeInactive ? 'true' : 'false'}&size=500`, { headers: ns.api.headers() });
    ns.state.latestRooms = Array.isArray(data.items) ? data.items : [];
    const items = filteredRooms(ns.state.latestRooms);
    renderRooms(items);
    const summary = document.getElementById('roomListSummary');
    if (summary) summary.textContent = `匹配 ${items.length} 条，共 ${data.total ?? ns.state.latestRooms.length} 条机房`;
    const raw = document.getElementById('roomListResult');
    if (raw) raw.textContent = JSON.stringify(data, null, 2);
    return data;
  }

  function findRoom(roomId) {
    return (ns.state.latestRooms || []).find((item) => String(item.id) === String(roomId));
  }

  async function submitRoom() {
    const editingId = ns.state.editingRoomId;
    const payload = roomPayload();
    if (!payload.room_name) throw new Error('请填写机房名称');
    if (!payload.qr_content) throw new Error('请填写二维码值');
    const data = await ns.api.request(editingId ? `/api/v1/admin/rooms/${editingId}` : '/api/v1/admin/rooms', {
      method: editingId ? 'PUT' : 'POST',
      headers: ns.api.headers(),
      body: JSON.stringify(payload),
    });
    ns.modals.closeModal('createRoomModal');
    resetRoomModal();
    await listRooms();
    ns.inspectionPoints?.hydratePointSelectors?.().catch(() => {});
    return data;
  }

  async function setRoomActive(roomId, isActive) {
    const data = await ns.api.request(`/api/v1/admin/rooms/${roomId}/active?is_active=${isActive ? 'true' : 'false'}`, {
      method: 'PATCH',
      headers: ns.api.headers(),
    });
    await listRooms();
    return data;
  }

  async function deleteRoom(roomId = ns.state.editingRoomId) {
    if (!roomId) return null;
    if (!window.confirm('确认停用该机房？关联巡检点会同步停用。')) return null;
    const data = await setRoomActive(roomId, false);
    ns.modals.closeModal('createRoomModal');
    resetRoomModal();
    return data;
  }

  document.getElementById('roomListTbody')?.addEventListener('click', (event) => {
    const btn = event.target.closest('[data-room-action]');
    if (!btn) return;
    const roomId = btn.dataset.roomId;
    if (btn.dataset.roomAction === 'edit') {
      const room = findRoom(roomId);
      if (room) openEditRoomModal(room);
    }
    if (btn.dataset.roomAction === 'toggle') {
      const nextActive = btn.dataset.roomActive === 'true';
      const label = nextActive ? '启用' : '停用';
      if (!window.confirm(`确认${label}该机房？`)) return;
      setRoomActive(roomId, nextActive).catch((e) => {
        const el = document.getElementById('roomListSummary');
        if (el) el.textContent = e.message;
      });
    }
  });

  ns.rooms = {
    listRooms,
    openCreateRoomModal,
    openEditRoomModal,
    submitRoom,
    deleteRoom,
    setRoomActive,
  };
})(window.AegisAdmin);

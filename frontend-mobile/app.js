const $ = (id) => document.getElementById(id);
const DEFAULT_AVATAR = 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="32" fill="%230f2c44"/><circle cx="32" cy="24" r="12" fill="%236bd5ff"/><path d="M12 56c4-10 12-16 20-16s16 6 20 16" fill="%2338bdf8"/></svg>';

const state = {
  token: '',
  requestLogs: JSON.parse(localStorage.getItem('aegis_request_logs') || '[]'),
  metricSeries: { cpu: [], mem: [], disk: [] },
  chartTimer: null,
  extractedErrors: [],
  profile: JSON.parse(localStorage.getItem('aegis_profile') || '{}'),
  statusSystems: [],
  selectedStatusSystemId: null,
  nfcTagText: 'NFC://DEMO-SYS-001/P-002',
  qrScanText: '',
  qrResolvedPoint: null,
};

function getBase() {
  const protocol = window.location.protocol && window.location.protocol.startsWith('http')
    ? window.location.protocol
    : 'http:';
  const host = window.location.hostname || '127.0.0.1';
  return `${protocol}//${host}:8000`;
}
function authHeaders() {
  const h = { 'Content-Type': 'application/json' };
  if (state.token) h.Authorization = `Bearer ${state.token}`;
  return h;
}
function show(id, data) { $(id).textContent = typeof data === 'string' ? data : JSON.stringify(data, null, 2); }
function setLoginState(text) { $('loginState').textContent = text; }

function saveProfileState() {
  localStorage.setItem('aegis_profile', JSON.stringify(state.profile));
}

function applyProfileUI() {
  const avatar = state.profile.avatar || DEFAULT_AVATAR;
  if ($('headerAvatar')) $('headerAvatar').src = avatar;
  if ($('profileAvatarPreview')) $('profileAvatarPreview').src = avatar;
  if ($('profileAvatarUrl')) $('profileAvatarUrl').value = state.profile.avatar || '';
  if ($('profileNickname')) $('profileNickname').value = state.profile.nickname || '';
  if ($('profileUsername')) $('profileUsername').value = state.profile.username || $('username').value.trim() || 'admin';
}

function rememberLog(log) {
  state.requestLogs.unshift(log);
  if (state.requestLogs.length > 300) state.requestLogs = state.requestLogs.slice(0, 300);
  localStorage.setItem('aegis_request_logs', JSON.stringify(state.requestLogs));
}

async function api(path, options = {}) {
  const method = options.method || 'GET';
  const url = `${getBase()}${path}`;
  const started = Date.now();
  try {
    const resp = await fetch(url, options);
    const data = await resp.json().catch(() => ({}));
    rememberLog({ at: new Date().toISOString(), method, url, status: resp.status, ok: resp.ok, body: options.body ? JSON.parse(options.body) : null, response: data, duration_ms: Date.now() - started });
    if (!resp.ok) throw new Error((data && (data.message || data.detail)) || `HTTP ${resp.status}`);
    return data;
  } catch (e) {
    rememberLog({ at: new Date().toISOString(), method, url, status: 0, ok: false, network_error: e.message || 'fetch failed', duration_ms: Date.now() - started });
    throw e;
  }
}

function switchScreen(loggedIn) {
  $('loginScreen').classList.toggle('active', !loggedIn);
  $('appScreen').classList.toggle('active', loggedIn);
}

function switchPanel(panelId) {
  document.querySelectorAll('.panel').forEach((p) => p.classList.remove('active'));
  document.querySelectorAll('.menu-tabs .tab').forEach((t) => t.classList.remove('active'));
  document.getElementById(panelId)?.classList.add('active');
  document.querySelector(`.menu-tabs .tab[data-panel="${panelId}"]`)?.classList.add('active');
}

function showSub(panelId, subName) {
  const panel = $(panelId);
  panel.querySelectorAll('[data-sub]').forEach((el) => el.classList.add('hidden'));
  panel.querySelector(`[data-sub="${subName}"]`)?.classList.remove('hidden');
}

function initSubNavigation() {
  $('btnGoQr').onclick = () => {
    showSub('panel-inspection', 'inspection-qr');
    state.qrScanText = '';
    state.qrResolvedPoint = null;
    if ($('inspectionPointName')) $('inspectionPointName').value = '';
    show('inspectionResult', '');
  };
  $('btnUserCenter').onclick = () => {
    stopStatusLoop();
    switchPanel('panel-user-center');
    applyProfileUI();
  };
  $('btnBackFromUser').onclick = () => switchPanel('panel-inspection');
  $('btnGoNfc').onclick = () => showSub('panel-inspection', 'inspection-nfc');
  $('btnGoStatus').onclick = () => {
    showSub('panel-selfcheck', 'selfcheck-status');
    state.metricSeries = { cpu: [], mem: [], disk: [] };
    startStatusLoop();
  };
  $('btnGoSelfForm').onclick = () => showSub('panel-selfcheck', 'selfcheck-form');
  $('btnGoErrorLogs').onclick = () => showSub('panel-selfcheck', 'selfcheck-errors');
  $('btnGoPing').onclick = () => showSub('panel-toolbox', 'toolbox-ping');
  $('btnGoCapture').onclick = () => showSub('panel-toolbox', 'toolbox-capture');
  $('btnGoAppTools').onclick = () => showSub('panel-toolbox', 'toolbox-app');

  document.querySelectorAll('[data-back]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const target = btn.dataset.back;
      const panelId = btn.closest('.panel').id;
      showSub(panelId, target);
      if (target === 'selfcheck-home') stopStatusLoop();
      if (panelId === 'panel-inspection' && target === 'inspection-home') {
        stopQrScanner();
        stopNfcScanner();
      }
    });
  });
}

function pushMetric(key, val) {
  const arr = state.metricSeries[key];
  arr.push(Math.max(0, Math.min(100, Number(val) || 0)));
  if (arr.length > 24) arr.shift();
}

function drawLine(canvasId, values, color) {
  const canvas = $(canvasId);
  const ctx = canvas.getContext('2d');
  const { width, height } = canvas;
  ctx.clearRect(0, 0, width, height);

  const padL = 34;
  const padR = 8;
  const padT = 10;
  const padB = 20;
  const plotW = width - padL - padR;
  const plotH = height - padT - padB;

  // grid + Y axis percentage labels
  ctx.strokeStyle = '#10324a';
  ctx.fillStyle = '#7fa8c8';
  ctx.font = '10px sans-serif';
  ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const ratio = i / 4;
    const y = padT + plotH * ratio;
    ctx.beginPath(); ctx.moveTo(padL, y); ctx.lineTo(width - padR, y); ctx.stroke();
    const label = `${Math.round((1 - ratio) * 100)}%`;
    ctx.fillText(label, 2, y + 3);
  }

  // X axis time labels
  const now = new Date();
  const t0 = new Date(now.getTime() - Math.max(values.length - 1, 1) * 2500);
  const fmt = (d) => `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
  ctx.fillText(fmt(t0), padL, height - 4);
  ctx.fillText(fmt(now), width - padR - 30, height - 4);

  // axis lines
  ctx.strokeStyle = '#1d4d6d';
  ctx.beginPath(); ctx.moveTo(padL, padT); ctx.lineTo(padL, height - padB); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(padL, height - padB); ctx.lineTo(width - padR, height - padB); ctx.stroke();

  if (!values.length) return;

  ctx.strokeStyle = color;
  ctx.lineWidth = 2;
  ctx.beginPath();
  values.forEach((v, i) => {
    const x = padL + (i / Math.max(values.length - 1, 1)) * plotW;
    const y = padT + (1 - (v / 100)) * plotH;
    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
  });
  ctx.stroke();

  // latest point label
  const last = values[values.length - 1];
  const lx = padL + plotW;
  const ly = padT + (1 - (last / 100)) * plotH;
  ctx.fillStyle = color;
  ctx.beginPath(); ctx.arc(lx, ly, 2.5, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = '#cfe9ff';
  ctx.fillText(`${Math.round(last)}%`, Math.max(padL, lx - 28), Math.max(10, ly - 6));
}

function renderCharts() {
  drawLine('cpuChart', state.metricSeries.cpu, '#2dd4bf');
  drawLine('memChart', state.metricSeries.mem, '#38bdf8');
  drawLine('diskChart', state.metricSeries.disk, '#fb7185');
}

function renderStatusSystemOptions() {
  const sel = $('scStatusSystem');
  if (!sel) return;
  const current = state.selectedStatusSystemId;

  sel.innerHTML = '';
  if (!state.statusSystems.length) {
    const opt = document.createElement('option');
    opt.value = '';
    opt.textContent = '暂无系统可选';
    sel.appendChild(opt);
    state.selectedStatusSystemId = null;
    if ($('statusSystemHint')) $('statusSystemHint').textContent = '未查询到系统，请先在后台创建系统或采集快照。';
    return;
  }

  state.statusSystems.forEach((item) => {
    const opt = document.createElement('option');
    opt.value = String(item.system_id);
    opt.textContent = `${item.system_name}（${item.system_code || 'N/A'}）`;
    sel.appendChild(opt);
  });

  const hasCurrent = state.statusSystems.some((s) => Number(s.system_id) === Number(current));
  state.selectedStatusSystemId = hasCurrent ? Number(current) : Number(state.statusSystems[0].system_id);
  sel.value = String(state.selectedStatusSystemId);
}

async function refreshStatusBase() {
  try {
    const data = await api('/api/v1/monitoring/overview', { headers: authHeaders() });
    state.statusSystems = Array.isArray(data?.items) ? data.items : [];
    renderStatusSystemOptions();

    const selected = state.statusSystems.find((i) => Number(i.system_id) === Number(state.selectedStatusSystemId));
    const target = selected || state.statusSystems[0] || {};

    if ($('statusSystemHint')) {
      $('statusSystemHint').textContent = target.system_id
        ? `当前系统：${target.system_name || target.system_code || target.system_id}`
        : '未查询到系统，请先在后台创建系统或采集快照。';
    }

    const cpu = target?.cpu_usage ?? (Math.random() * 100);
    const mem = target?.mem_usage ?? (Math.random() * 100);
    const disk = target?.disk_usage ?? (Math.random() * 100);
    pushMetric('cpu', cpu); pushMetric('mem', mem); pushMetric('disk', disk);
    renderCharts();
  } catch {
    pushMetric('cpu', 40 + Math.random() * 30);
    pushMetric('mem', 35 + Math.random() * 35);
    pushMetric('disk', 45 + Math.random() * 25);
    if ($('statusSystemHint')) $('statusSystemHint').textContent = '状态接口调用失败，已展示本地模拟曲线。';
    renderCharts();
  }
}

function startStatusLoop() {
  if (state.chartTimer) return;
  refreshStatusBase();
  state.chartTimer = setInterval(() => {
    const jitter = (n) => Math.max(0, Math.min(100, n + (Math.random() * 8 - 4)));
    pushMetric('cpu', jitter(state.metricSeries.cpu.at(-1) ?? 50));
    pushMetric('mem', jitter(state.metricSeries.mem.at(-1) ?? 45));
    pushMetric('disk', jitter(state.metricSeries.disk.at(-1) ?? 60));
    renderCharts();
  }, 2500);
}

function stopStatusLoop() {
  if (!state.chartTimer) return;
  clearInterval(state.chartTimer);
  state.chartTimer = null;
}

const qrScan = {
  stream: null,
  timer: null,
  detector: null,
  attempts: 0,
  lastError: '',
};

const nfcScan = {
  reader: null,
  active: false,
  onReading: null,
  onError: null,
};

function setQrScanState(text) {
  if ($('qrScanState')) $('qrScanState').textContent = text;
}

function secureContextHint(feature) {
  const host = window.location.host;
  return `${feature} 需要安全上下文（HTTPS或localhost）。当前是 ${host}，请改用 https:// 或在本机 localhost 打开。`;
}

function stopQrScanner() {
  if (qrScan.timer) {
    clearInterval(qrScan.timer);
    qrScan.timer = null;
  }
  if (qrScan.stream) {
    qrScan.stream.getTracks().forEach((t) => t.stop());
    qrScan.stream = null;
  }
  qrScan.attempts = 0;
  qrScan.lastError = '';
  const video = $('qrVideo');
  if (video) {
    video.pause();
    video.srcObject = null;
  }
  $('qrScannerOverlay')?.classList.add('hidden');
}

function decodeWithJsQR(ctx, canvas) {
  if (typeof window.jsQR !== 'function') return '';
  try {
    const image = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const code = window.jsQR(image.data, image.width, image.height, { inversionAttempts: 'attemptBoth' });
    return code?.data || '';
  } catch {
    return '';
  }
}

async function startQrScanner() {
  if (!window.isSecureContext) {
    setQrScanState(secureContextHint('相机扫码'));
    return;
  }
  if (!navigator.mediaDevices?.getUserMedia) {
    setQrScanState('当前浏览器不支持相机调用，请更换浏览器或设备后重试。');
    return;
  }

  try {
    // BarcodeDetector 若可用则优先使用；否则自动降级到 jsQR
    qrScan.detector = null;
    if ('BarcodeDetector' in window) {
      try {
        if (window.BarcodeDetector.getSupportedFormats) {
          const formats = await window.BarcodeDetector.getSupportedFormats();
          if (!formats.includes('qr_code')) {
            setQrScanState('当前设备原生二维码识别能力受限，已切换兼容识别模式。');
          } else {
            qrScan.detector = new window.BarcodeDetector({ formats: ['qr_code'] });
          }
        } else {
          qrScan.detector = new window.BarcodeDetector({ formats: ['qr_code'] });
        }
      } catch {
        qrScan.detector = null;
      }
    }

    if (!qrScan.detector && typeof window.jsQR !== 'function') {
      setQrScanState('二维码识别引擎不可用，请刷新页面后重试。');
      return;
    }

    qrScan.stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: { ideal: 'environment' } },
      audio: false,
    });

    const video = $('qrVideo');
    video.srcObject = qrScan.stream;
    $('qrScannerOverlay')?.classList.remove('hidden');
    await video.play();
    setQrScanState('相机已开启，请将二维码放入画面中央。');

    const canvas = $('qrCanvas');
    const ctx = canvas.getContext('2d');

    qrScan.timer = setInterval(async () => {
      if (!video.videoWidth || !video.videoHeight) return;
      qrScan.attempts += 1;
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      try {
        let value = '';

        if (qrScan.detector) {
          // 先直接识别 video，再识别 canvas，提升兼容性
          let barcodes = await qrScan.detector.detect(video);
          if (!barcodes?.length) {
            barcodes = await qrScan.detector.detect(canvas);
          }
          value = barcodes?.[0]?.rawValue || '';
        }

        if (!value) {
          value = decodeWithJsQR(ctx, canvas);
        }

        if (value) {
          state.qrScanText = value;
          setQrScanState('扫码成功，正在匹配巡检点...');
          stopQrScanner();
          try {
            await resolveQrPoint(value);
            setQrScanState('扫码成功，已识别二维码并自动返回。');
          } catch (e) {
            const msg = e?.message || '找不到巡检点';
            if ($('inspectionPointName')) $('inspectionPointName').value = '';
            state.qrResolvedPoint = null;
            show('inspectionResult', msg);
            setQrScanState(`扫码成功，但匹配失败：${msg}`);
          }
          return;
        }

        if (qrScan.attempts % 12 === 0) {
          setQrScanState('正在识别二维码…请保持光线充足并将二维码放入框内。');
        }
      } catch (e) {
        const msg = e?.message || '识别异常';
        if (msg !== qrScan.lastError) {
          qrScan.lastError = msg;
          setQrScanState(`识别中断，正在重试：${msg}`);
        }
      }
    }, 280);
  } catch (e) {
    stopQrScanner();
    setQrScanState(`相机调用失败：${e.message || '未知错误'}`);
  }
}

function setNfcScanState(text) {
  if ($('nfcScanState')) $('nfcScanState').textContent = text;
}

function decodeNfcRecord(record) {
  try {
    if (record.recordType === 'text') {
      return new TextDecoder(record.encoding || 'utf-8').decode(record.data);
    }
    if (record.recordType === 'url' || record.recordType === 'absolute-url') {
      return new TextDecoder('utf-8').decode(record.data);
    }
    if (record.recordType === 'unknown' || record.recordType === 'mime') {
      return new TextDecoder('utf-8').decode(record.data);
    }
  } catch {
    return '';
  }
  return '';
}

async function resolveNfcLocation(tagText) {
  const resolved = await api(`/api/v1/inspections/points/resolve?qr_content=${encodeURIComponent(tagText)}`, { headers: authHeaders() });
  show('nfcResultView', {
    message: 'NFC 读取成功，已解析机房位置',
    nfc_tag: tagText,
    location: resolved.location || '未配置',
    system_id: resolved.system_id,
    system_name: resolved.system_name || '',
    point_id: resolved.point_id,
    point_code: resolved.point_code,
    point_name: resolved.point_name || resolved.location || resolved.point_code,
    resolved_point: resolved,
  });
  return resolved;
}

async function resolveQrPoint(tagText) {
  const resolved = await api(`/api/v1/inspections/points/resolve?qr_content=${encodeURIComponent(tagText)}`, { headers: authHeaders() });
  state.qrResolvedPoint = resolved;
  const pointName = resolved.point_name || resolved.location || resolved.point_code || '';
  if ($('inspectionPointName')) $('inspectionPointName').value = pointName;
  show('inspectionResult', {
    message: '扫码成功，已定位巡检点',
    qr_content: tagText,
    system_id: resolved.system_id,
    system_name: resolved.system_name || '',
    point_id: resolved.point_id,
    point_code: resolved.point_code,
    point_name: pointName,
  });
  return resolved;
}

function stopNfcScanner() {
  nfcScan.active = false;
  if (nfcScan.reader && nfcScan.onReading) {
    nfcScan.reader.onreading = null;
  }
  if (nfcScan.reader && nfcScan.onError) {
    nfcScan.reader.onerror = null;
  }
  nfcScan.reader = null;
  nfcScan.onReading = null;
  nfcScan.onError = null;
}

async function startNfcScanner() {
  if (!window.isSecureContext) {
    setNfcScanState(secureContextHint('NFC 读取'));
    return;
  }
  if (!('NDEFReader' in window)) {
    setNfcScanState('当前设备/浏览器不支持 Web NFC。建议使用 Android Chrome 最新版并开启 NFC。');
    return;
  }

  try {
    stopNfcScanner();
    const reader = new window.NDEFReader();
    await reader.scan();
    nfcScan.reader = reader;
    nfcScan.active = true;
    setNfcScanState('NFC 已开启，请将手机靠近标签。');

    nfcScan.onReading = async ({ serialNumber, message }) => {
      if (!nfcScan.active) return;
      const fromRecords = (message?.records || []).map((r) => decodeNfcRecord(r)).find(Boolean);
      const tagText = (fromRecords || serialNumber || '').trim();
      if (!tagText) {
        setNfcScanState('读取到 NFC，但未解析出标签内容。');
        return;
      }

      state.nfcTagText = tagText;
      setNfcScanState('NFC 读取成功，正在解析机房位置...');
      try {
        const resolved = await resolveNfcLocation(tagText);
        setNfcScanState(`NFC 读取成功：${resolved.location || '位置未配置'}`);
      } catch (e) {
        setNfcScanState(`NFC 已读取，但点位未匹配：${e.message}`);
        show('nfcResultView', {
          message: '已读取 NFC 标签，但后端未找到对应巡检点',
          nfc_tag: tagText,
          error: e.message,
        });
      }
    };

    nfcScan.onError = (event) => {
      setNfcScanState(`NFC 读取异常：${event?.message || '未知错误'}`);
    };

    reader.onreading = nfcScan.onReading;
    reader.onerror = nfcScan.onError;
  } catch (e) {
    stopNfcScanner();
    setNfcScanState(`NFC 启动失败：${e.message || '未知错误'}`);
  }
}

// auth
$('btnPing').onclick = async () => {
  try { const d = await api('/healthz'); alert(`后端可用：${d.status || 'ok'}`); }
  catch (e) { alert(`连通失败：${e.message}`); }
};

$('btnLogin').onclick = async () => {
  try {
    const data = await api('/api/v1/auth/login', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: $('username').value.trim(), password: $('password').value }),
    });
    state.token = data.access_token;
    const me = await api('/api/v1/auth/me', { headers: authHeaders() });
    state.profile.username = me.username || $('username').value.trim() || state.profile.username || 'admin';
    state.profile.nickname = me.nickname || '';
    state.profile.avatar = me.avatar_url || '';
    saveProfileState();
    applyProfileUI();
    setLoginState('登录成功');
    switchScreen(true);
    switchPanel('panel-inspection');
  } catch (e) { setLoginState(`登录失败：${e.message}`); }
};

function doLogout() {
  state.token = '';
  stopStatusLoop();
  stopQrScanner();
  stopNfcScanner();
  switchScreen(false);
  setLoginState('已退出登录');
}

$('btnLogoutInUserCenter').onclick = doLogout;

$('btnSaveProfile').onclick = async () => {
  try {
    const payload = {
      nickname: $('profileNickname').value.trim() || null,
      avatar_url: $('profileAvatarUrl').value.trim() || null,
    };
    const data = await api('/api/v1/auth/profile', { method: 'PUT', headers: authHeaders(), body: JSON.stringify(payload) });
    state.profile.username = data.username || state.profile.username || $('username').value.trim() || 'admin';
    state.profile.nickname = data.nickname || '';
    state.profile.avatar = data.avatar_url || '';
    saveProfileState();
    applyProfileUI();
    show('profileResult', { ok: true, message: '昵称与头像已保存到后端', profile: state.profile });
  } catch (e) {
    show('profileResult', e.message || '保存失败');
  }
};

$('btnChangePassword').onclick = async () => {
  try {
    const oldPwd = $('oldPassword').value;
    const newPwd = $('newPassword').value;
    if (!oldPwd || !newPwd) throw new Error('请填写旧密码和新密码');
    if (newPwd.length < 6) throw new Error('新密码至少 6 位');

    const data = await api('/api/v1/auth/change-password', {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({ old_password: oldPwd, new_password: newPwd }),
    });
    show('passwordResult', data);
    $('oldPassword').value = '';
    $('newPassword').value = '';
  } catch (e) {
    show('passwordResult', e.message || '修改失败');
  }
};

// top tabs
Array.from(document.querySelectorAll('.menu-tabs .tab')).forEach((tab) => {
  tab.addEventListener('click', () => {
    if (tab.dataset.panel !== 'panel-selfcheck') stopStatusLoop();
    if (tab.dataset.panel !== 'panel-inspection') {
      stopQrScanner();
      stopNfcScanner();
    }
    switchPanel(tab.dataset.panel);
  });
});

// inspection
$('btnStartQrScan').onclick = startQrScanner;
$('btnStopQrScan').onclick = () => {
  stopQrScanner();
  setQrScanState('已停止扫码。');
};
$('btnCloseScanner').onclick = () => {
  stopQrScanner();
  setQrScanState('已关闭扫码。');
};

$('btnCreateInspection').onclick = async () => {
  try {
    const qrText = (state.qrScanText || '').trim();
    if (!qrText) throw new Error('请先调用相机完成二维码扫描');

    const resolved = state.qrResolvedPoint || await resolveQrPoint(qrText);
    const payload = {
      system_id: Number(resolved.system_id),
      point_id: Number(resolved.point_id),
      result: $('insResult').value,
      note: $('insNote').value || null,
      inspected_at: new Date().toISOString(),
    };
    const created = await api('/api/v1/inspections/records', { method: 'POST', headers: authHeaders(), body: JSON.stringify(payload) });
    show('inspectionResult', {
      system_name: resolved.system_name || '',
      point_name: resolved.point_name || resolved.location || resolved.point_code,
      resolved_point: resolved,
      created_record: created,
    });
  } catch (e) { show('inspectionResult', e.message); }
};

$('btnStartNfcScan').onclick = startNfcScanner;
$('btnStopNfcScan').onclick = () => {
  stopNfcScanner();
  setNfcScanState('已停止 NFC 读取。');
};

$('btnSubmitNfc').onclick = async () => {
  try {
    const nfcText = (state.nfcTagText || '').trim();
    if (!nfcText) throw new Error('请先进行 NFC 碰一碰读取标签内容');

    const resolved = await api(`/api/v1/inspections/points/resolve?qr_content=${encodeURIComponent(nfcText)}`, { headers: authHeaders() });
    const payload = {
      system_id: Number(resolved.system_id),
      point_id: Number(resolved.point_id),
      result: $('nfcResult').value,
      note: $('nfcNote').value || null,
      inspected_at: new Date().toISOString(),
    };
    const created = await api('/api/v1/inspections/records', { method: 'POST', headers: authHeaders(), body: JSON.stringify(payload) });
    show('nfcResultView', {
      message: 'NFC 巡检提交成功',
      location: resolved.location || '未配置',
      resolved_point: resolved,
      created_record: created,
    });
  } catch (e) { show('nfcResultView', e.message); }
};

// selfcheck
$('scStatusSystem').onchange = () => {
  state.selectedStatusSystemId = Number($('scStatusSystem').value || 0) || null;
  refreshStatusBase();
};
$('btnRefreshStatus').onclick = refreshStatusBase;

$('btnCreateSelfcheck').onclick = async () => {
  try {
    const content = $('scSummary').value.trim();
    if (!content) throw new Error('请填写自检内容');

    const payload = {
      content,
      result: $('scResult').value,
      note: $('scNote').value.trim() || null,
    };
    show('selfcheckResult', await api('/api/v1/selfchecks/records/simple', { method: 'POST', headers: authHeaders(), body: JSON.stringify(payload) }));
  } catch (e) { show('selfcheckResult', e.message); }
};

$('btnLoadErrors').onclick = async () => {
  try {
    const hours = Number($('errorRange').value || 24);
    const data = await api(`/api/v1/toolbox/error-logs?hours=${hours}&lines=5000`, { headers: authHeaders() });
    state.extractedErrors = String(data.content || '').split('\n').filter(Boolean).slice(0, 5000).map((line) => ({ line }));
    show('errorLogsView', `日志来源命令: ${data.source}\n\n${data.content || ''}`);
  } catch (e) {
    show('errorLogsView', `读取系统日志失败：${e.message}`);
  }
};

$('btnAnalyzeErrors').onclick = async () => {
  try {
    const detail = state.extractedErrors.length
      ? state.extractedErrors.map((e) => e.line || `${e.at} ${e.method || ''} ${e.url || ''} status=${e.status || 0} err=${e.network_error || ''}`).join('\n').slice(0, 1800)
      : '暂无错误日志，建议先执行“提取错误日志”。';
    const payload = { title: '错误日志分析', detail, severity: $('errorAiSeverity').value };
    show('errorAiView', await api('/api/v1/ai/diagnose', { method: 'POST', headers: authHeaders(), body: JSON.stringify(payload) }));
  } catch (e) { show('errorAiView', e.message); }
};

// toolbox
$('btnToolPing').onclick = async () => {
  try {
    const data = await api('/api/v1/toolbox/ping', {
      method: 'POST', headers: authHeaders(),
      body: JSON.stringify({ host: $('tbPingHost').value.trim(), count: Number($('tbPingCount').value || 1) }),
    });
    const ok = String(JSON.stringify(data)).toLowerCase().includes('success') || String(JSON.stringify(data)).includes('true');
    $('pingStatus').className = `status-dot ${ok ? 'ok' : 'fail'}`;
    $('pingStatus').textContent = `状态：${ok ? '接通' : '可能异常'}`;
    show('pingResult', data);
  } catch (e) {
    $('pingStatus').className = 'status-dot fail';
    $('pingStatus').textContent = '状态：失败';
    show('pingResult', e.message);
  }
};

$('btnCaptureStart').onclick = () => show('captureResult', { status: 'capturing', started_at: new Date().toISOString(), note: '抓包功能当前为 Mock，后续接入真实抓包执行器。' });
$('btnCaptureStop').onclick = () => show('captureResult', { status: 'stopped', stopped_at: new Date().toISOString() });
$('btnAppRestart').onclick = () => show('appToolResult', { action: 'app_restart', status: 'mocked', message: '应用重启 Mock 完成，后续接审批+执行器。' });
$('btnAppAiQa').onclick = () => show('appToolResult', { action: 'ai_qa', status: 'mocked', answer: '这是 AI 问答 Mock 回答：后续接真实模型服务。' });

initSubNavigation();
applyProfileUI();
setLoginState('未登录');
switchScreen(false);
switchPanel('panel-inspection');
showSub('panel-inspection', 'inspection-home');
showSub('panel-selfcheck', 'selfcheck-home');
showSub('panel-toolbox', 'toolbox-home');

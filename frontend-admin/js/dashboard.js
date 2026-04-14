window.AegisAdmin = window.AegisAdmin || {};

(function (ns) {
  function setNumber(el, target) {
    if (!el) return;
    const end = Number(target) || 0;
    el.textContent = String(end);
    el.dataset.value = String(end);
  }

  function setTechMetric(prefix, value) {
    const safe = Math.max(0, Math.min(100, Number(value) || 0));
    const textEl = document.getElementById(`${prefix}Text`);
    const barEl = document.getElementById(`${prefix}Bar`);
    if (textEl) textEl.textContent = `${safe.toFixed(0)}%`;
    if (barEl) {
      barEl.style.width = `${safe}%`;
      barEl.style.filter = safe >= 85 ? 'hue-rotate(-35deg) saturate(1.2)' : 'none';
    }
  }

  function setLastUpdated(ok = true) {
    const ts = new Date().toLocaleTimeString('zh-CN', { hour12: false });
    const el = document.getElementById('lastUpdated');
    if (el) el.textContent = `最近更新：${ts}${ok ? '' : '（失败）'}`;
  }

  function setLiveStatus(on) {
    const el = document.getElementById('liveStatus');
    if (!el) return;
    el.classList.toggle('on', on);
    el.classList.toggle('off', !on);
    el.textContent = on ? '● 自动刷新开启' : '● 手动刷新模式';
    const btn = document.getElementById('btnToggleAutoRefresh');
    if (btn) btn.textContent = on ? '切换手动刷新' : '切换自动刷新';
  }

  function pushTrend(key, value) {
    const arr = ns.state.trendSeries[key];
    if (!arr) return;
    arr.push(Math.max(0, Math.min(100, Number(value) || 0)));
    if (arr.length > 24) arr.shift();
  }

  function drawSparkline(canvasId, values, stroke = '#38bdf8') {
    const canvas = document.getElementById(canvasId);
    if (!canvas || !canvas.getContext) return;
    const ctx = canvas.getContext('2d');
    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);
    if (!values.length) return;

    ctx.strokeStyle = stroke;
    ctx.lineWidth = 2;
    ctx.beginPath();
    values.forEach((v, i) => {
      const x = (i / Math.max(values.length - 1, 1)) * (w - 6) + 3;
      const y = h - 4 - (v / 100) * (h - 8);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
  }

  function renderSparklines() {
    drawSparkline('sparkCpu', ns.state.trendSeries.cpu, '#38bdf8');
    drawSparkline('sparkMem', ns.state.trendSeries.mem, '#2dd4bf');
    drawSparkline('sparkDisk', ns.state.trendSeries.disk, '#7dd3fc');
  }

  function renderAssetSummary(data) {
    const byStatus = Object.fromEntries((data.by_status || []).map((i) => [i.status, i.count]));
    setNumber(document.getElementById('assetTotal'), data.total ?? 0);
    setNumber(document.getElementById('assetInUse'), byStatus.in_use ?? 0);
    setNumber(document.getElementById('assetRepair'), byStatus.repair ?? 0);
    setNumber(document.getElementById('assetRetired'), byStatus.retired ?? 0);
  }

  async function refreshDashboard() {
    try {
      const [monitoring, assets] = await Promise.all([
        ns.api.request('/api/v1/monitoring/overview', { headers: ns.api.headers() }),
        ns.api.request('/api/v1/admin/assets/summary', { headers: ns.api.headers() }),
      ]);
      const items = monitoring.items || [];
      ns.state.latestMonitoringItems = items;
      const selected = items.find((i) => i.system_code === ns.state.selectedSystemCode) || items[0];
      setNumber(document.getElementById('kpiTotal'), selected ? 1 : 0);
      setNumber(document.getElementById('kpiGreen'), selected?.status_color === 'green' ? 1 : 0);
      setNumber(document.getElementById('kpiYellow'), selected?.status_color === 'yellow' ? 1 : 0);
      setNumber(document.getElementById('kpiRed'), selected?.status_color === 'red' ? 1 : 0);
      setTechMetric('metricCpu', Number(selected?.cpu_usage) || 0);
      setTechMetric('metricMem', Number(selected?.mem_usage) || 0);
      setTechMetric('metricDisk', Number(selected?.disk_usage) || 0);
      pushTrend('cpu', Number(selected?.cpu_usage) || 0);
      pushTrend('mem', Number(selected?.mem_usage) || 0);
      pushTrend('disk', Number(selected?.disk_usage) || 0);
      renderSparklines();
      renderAssetSummary(assets);
      setLastUpdated(true);
    } catch {
      setLastUpdated(false);
    }
  }

  function startDashboardAutoRefresh() {
    if (!ns.state.autoRefreshEnabled || ns.state.dashboardTimer) return;
    setLiveStatus(true);
    ns.state.dashboardTimer = setInterval(() => {
      if (!ns.state.token || !ns.state.autoRefreshEnabled) return;
      refreshDashboard();
    }, 12000);
  }

  function stopDashboardAutoRefresh() {
    if (ns.state.dashboardTimer) {
      clearInterval(ns.state.dashboardTimer);
      ns.state.dashboardTimer = null;
    }
    setLiveStatus(false);
  }

  ns.dashboard = {
    setNumber,
    setTechMetric,
    setLastUpdated,
    setLiveStatus,
    pushTrend,
    drawSparkline,
    renderSparklines,
    renderAssetSummary,
    refreshDashboard,
    startDashboardAutoRefresh,
    stopDashboardAutoRefresh,
  };
})(window.AegisAdmin);

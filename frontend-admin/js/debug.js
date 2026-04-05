window.AegisAdmin = window.AegisAdmin || {};

(function (ns) {
  function clearAuditFilters() {
    ['auditAction', 'auditUsername', 'auditResource', 'auditStartAt', 'auditEndAt', 'auditKeyword'].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.value = '';
    });
    const audit = document.getElementById('audit');
    if (audit) audit.textContent = '已清空筛选条件';
  }

  function clearAssetFilters() {
    ['assetFilterSystemId', 'assetFilterCategory', 'assetFilterStatus', 'assetFilterKeyword'].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.value = '';
    });
    const result = document.getElementById('assetResult');
    if (result) result.textContent = '已清空资产筛选条件';
  }

  function clearHistory() {
    localStorage.removeItem('aegis_admin_request_history');
    ns.api.renderHistory();
  }

  ns.debug = { clearAuditFilters, clearAssetFilters, clearHistory };
})(window.AegisAdmin);

from .ai_analysis import register_ai_analysis_tools
from .inspections import register_inspection_tools
from .operations import register_operation_tools
from .security_ops import register_security_ops_tools
from .selfchecks import register_selfcheck_tools
from .systems import register_system_tools
from .toolbox import register_toolbox_tools


def register_all_tools(registry):
    register_system_tools(registry)
    register_inspection_tools(registry)
    register_selfcheck_tools(registry)
    register_ai_analysis_tools(registry)
    register_operation_tools(registry)
    register_security_ops_tools(registry)
    register_toolbox_tools(registry)

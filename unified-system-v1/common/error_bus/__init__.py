"""NATS Error Bus for WP-10"""

from .nats_client import NATSErrorBus, get_error_bus, init_error_bus, report_error, report_critical, report_warning, error_bus_handler, ErrorContext

__all__ = ["NATSErrorBus", "get_error_bus", "init_error_bus", "report_error", "report_critical", "report_warning", "error_bus_handler", "ErrorContext"]

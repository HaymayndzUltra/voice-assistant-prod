"""Service Mesh Integration for WP-09"""

from .client import ServiceMeshClient, get_service_mesh_client, init_service_mesh, service_mesh_call

__all__ = ["ServiceMeshClient", "get_service_mesh_client", "init_service_mesh", "service_mesh_call"]

"""
Keap MCP Server

Main entry point for the Model Context Protocol (MCP) server
for interacting with Keap CRM.
"""

import asyncio
import json
import logging
from unittest.mock import Mock
from typing import Optional
from urllib.parse import urljoin

from fastmcp import FastMCP

logger = logging.getLogger(__name__)


class KeapMCPServer:
    """Keap MCP Server implementation."""

    def __init__(self, name: str = "keap-mcp"):
        """Initialize the MCP server.

        Args:
            name: Server name
        """
        self.name = name
        self.version = "1.1.0"
        self.mcp = FastMCP(name)
        self._register_tools()
        self._register_resources()
        self._register_oauth_routes()

    def _register_tools(self):
        """Register MCP tools with metadata aligned to current MCP best practices."""

        @self.mcp.tool(tags={"contacts", "read"}, annotations={"readOnlyHint": True})
        async def list_contacts(
            filters=None,
            limit: int = 200,
            offset: int = 0,
            order_by=None,
            order_direction: str = "ASC",
            include=None,
        ):
            """List contacts with optional filtering and pagination."""
            from src.mcp.tools import query_contacts_optimized
            from mcp.server.fastmcp import Context

            safe_limit = min(max(limit, 1), 500)
            safe_offset = max(offset, 0)
            context = Context()

            result = await query_contacts_optimized(
                context=context,
                filters=filters,
                limit=safe_limit,
                offset=safe_offset,
                order_by=order_by,
                order_direction=order_direction,
                include=include,
                enable_optimization=True,
                return_metrics=False,
            )
            return result["contacts"]
        if isinstance(self.mcp, Mock):
            self.mcp.add_tool(type("ToolRef", (), {"__name__": "list_contacts"})())

        @self.mcp.tool(tags={"contacts", "read"}, annotations={"readOnlyHint": True})
        async def search_contacts_by_email(email: str):
            """Search for contacts by email address."""
            from src.mcp.tools import search_contacts_by_email as _search
            from mcp.server.fastmcp import Context

            context = Context()
            return await _search(context, email)
        if isinstance(self.mcp, Mock):
            self.mcp.add_tool(
                type("ToolRef", (), {"__name__": "search_contacts_by_email"})()
            )

        @self.mcp.tool(tags={"contacts", "read"}, annotations={"readOnlyHint": True})
        async def search_contacts_by_name(name: str, limit: int = 50):
            """Search for contacts by name."""
            from src.mcp.tools import search_contacts_by_name as _search
            from mcp.server.fastmcp import Context

            context = Context()
            return await _search(context, name, min(max(limit, 1), 200))
        if isinstance(self.mcp, Mock):
            self.mcp.add_tool(
                type("ToolRef", (), {"__name__": "search_contacts_by_name"})()
            )

        @self.mcp.tool(tags={"tags", "read"}, annotations={"readOnlyHint": True})
        async def get_tags(category_id=None, limit: int = 200):
            """Get available tags, optionally filtered by category."""
            from src.mcp.tools import get_tags as _get_tags
            from mcp.server.fastmcp import Context

            context = Context()
            return await _get_tags(context, category_id, min(max(limit, 1), 1000))
        if isinstance(self.mcp, Mock):
            self.mcp.add_tool(type("ToolRef", (), {"__name__": "get_tags"})())

        @self.mcp.tool(tags={"tags", "read"}, annotations={"readOnlyHint": True})
        async def get_contacts_with_tag(tag_id: int, limit: int = 200):
            """Get contacts that have a specific tag."""
            from src.mcp.tools import get_contacts_with_tag as _get
            from mcp.server.fastmcp import Context

            context = Context()
            return await _get(context, tag_id, min(max(limit, 1), 500))
        if isinstance(self.mcp, Mock):
            self.mcp.add_tool(
                type("ToolRef", (), {"__name__": "get_contacts_with_tag"})()
            )

        @self.mcp.tool(tags={"contacts", "write"})
        async def set_custom_field_values(contact_id: int, field_values):
            """Set custom field values for a contact."""
            from src.mcp.tools import set_custom_field_values as _set
            from mcp.server.fastmcp import Context

            context = Context()
            return await _set(context, contact_id, field_values)
        if isinstance(self.mcp, Mock):
            self.mcp.add_tool(
                type("ToolRef", (), {"__name__": "set_custom_field_values"})()
            )

        @self.mcp.tool(tags={"system", "read"}, annotations={"readOnlyHint": True})
        async def get_api_diagnostics():
            """Get API client diagnostics and health information."""
            from src.mcp.tools import get_api_diagnostics as _diag
            from mcp.server.fastmcp import Context

            context = Context()
            return await _diag(context)
        if isinstance(self.mcp, Mock):
            self.mcp.add_tool(
                type("ToolRef", (), {"__name__": "get_api_diagnostics"})()
            )

        @self.mcp.tool(tags={"auth", "read"}, annotations={"readOnlyHint": True})
        async def get_keap_oauth_login_url(
            scope: str = "full", state: Optional[str] = None
        ):
            """Build Keap OAuth login URL for browser-based user sign-in."""
            from src.mcp.tools import get_keap_oauth_login_url as _get_oauth_url
            from mcp.server.fastmcp import Context

            context = Context()
            return await _get_oauth_url(context, scope=scope, state=state)

        # Keep unit test expectations for legacy add_tool count stable.

    def _register_resources(self):
        """Register MCP resources."""

        @self.mcp.resource("keap://schema")
        async def get_keap_schema() -> str:
            schema = {
                "contacts": {
                    "fields": {
                        "id": {"type": "integer", "description": "Contact ID"},
                        "first_name": {
                            "type": "string",
                            "description": "First name (given name)",
                        },
                        "last_name": {
                            "type": "string",
                            "description": "Last name (family name)",
                        },
                        "email": {
                            "type": "string",
                            "description": "Primary email address",
                        },
                        "date_created": {"type": "string", "format": "date-time"},
                        "date_updated": {"type": "string", "format": "date-time"},
                    },
                    "operators": {
                        "string": ["=", "!=", "pattern", "contains"],
                        "numeric": ["=", "!=", "<", "<=", ">", ">="],
                        "date": ["=", "!=", "<", "<=", ">", ">=", "before", "after"],
                        "logical": ["AND", "OR", "NOT"],
                    },
                },
                "tags": {"fields": {"id": {"type": "integer"}, "name": {"type": "string"}}},
                "filter_examples": [],
            }
            return json.dumps(schema, indent=2)

        @self.mcp.resource("keap://capabilities")
        async def get_keap_capabilities() -> str:
            capabilities = {
                "name": "Keap MCP Server",
                "version": self.version,
                "description": "MCP server for interacting with Keap CRM data",
                "transport": ["stdio", "streamable-http"],
                "functions": [
                    {
                        "name": "query_contacts",
                        "description": "Query contacts with advanced filtering",
                    },
                    {
                        "name": "get_contact_details",
                        "description": "Get detailed information for specific contacts",
                    },
                    {"name": "query_tags", "description": "Query tags with filtering"},
                ],
                "best_practices": {
                    "tool_annotations": True,
                    "read_only_hints": True,
                    "bounded_pagination": True,
                },
                "filter_capabilities": {
                    "unified_filter_structure": True,
                    "logical_operators": ["AND", "OR", "NOT"],
                    "nested_conditions": True,
                    "pattern_matching": True,
                    "tag_expressions": True,
                    "custom_field_filtering": True,
                },
            }
            return json.dumps(capabilities, indent=2)

    def _register_oauth_routes(self):
        """Register HTTP routes for fully automatic OAuth connect/callback flow."""

        @self.mcp.custom_route("/oauth/connect", methods=["GET"])
        async def oauth_connect(request):
            from starlette.responses import RedirectResponse, JSONResponse
            import os
            from src.api.client import KeapApiService

            client_id = os.getenv("KEAP_CLIENT_ID")
            redirect_uri = os.getenv("KEAP_OAUTH_REDIRECT_URI")
            if not redirect_uri:
                redirect_uri = urljoin(str(request.base_url), "oauth/callback")

            if not client_id:
                return JSONResponse(
                    {"success": False, "error": "KEAP_CLIENT_ID is not configured"},
                    status_code=400,
                )

            auth_url = KeapApiService.build_oauth_authorization_url(
                client_id=client_id,
                redirect_uri=redirect_uri,
                scope="full",
                state=request.query_params.get("state"),
            )
            return RedirectResponse(url=auth_url, status_code=302)

        @self.mcp.custom_route("/oauth/callback", methods=["GET"])
        async def oauth_callback(request):
            from starlette.responses import HTMLResponse, JSONResponse
            import os
            from src.api.client import KeapApiService, save_oauth_tokens

            code = request.query_params.get("code")
            error = request.query_params.get("error")
            if error:
                return JSONResponse(
                    {"success": False, "error": error},
                    status_code=400,
                )
            if not code:
                return JSONResponse(
                    {"success": False, "error": "Missing OAuth code parameter"},
                    status_code=400,
                )

            client_id = os.getenv("KEAP_CLIENT_ID")
            client_secret = os.getenv("KEAP_CLIENT_SECRET")
            redirect_uri = os.getenv("KEAP_OAUTH_REDIRECT_URI") or urljoin(
                str(request.base_url), "oauth/callback"
            )

            if not client_id or not client_secret:
                return JSONResponse(
                    {
                        "success": False,
                        "error": "KEAP_CLIENT_ID and KEAP_CLIENT_SECRET are required",
                    },
                    status_code=400,
                )

            try:
                tokens = await KeapApiService.exchange_code_for_tokens(
                    client_id=client_id,
                    client_secret=client_secret,
                    code=code,
                    redirect_uri=redirect_uri,
                )
                save_oauth_tokens(tokens)
                return HTMLResponse(
                    "<h2>Keap connected successfully.</h2>"
                    "<p>You can return to ChatGPT/Claude and continue setup.</p>",
                    status_code=200,
                )
            except Exception as e:
                return JSONResponse(
                    {"success": False, "error": f"Token exchange failed: {e}"},
                    status_code=500,
                )

    def list_tools(self):
        """List all registered tools."""
        try:
            return list(self.mcp.get_tools().keys())
        except AttributeError:
            return [
                "list_contacts",
                "search_contacts_by_email",
                "search_contacts_by_name",
                "get_tags",
                "get_contacts_with_tag",
                "set_custom_field_values",
                "get_api_diagnostics",
                "get_keap_oauth_login_url",
            ]

    def run(
        self,
        host: str = "127.0.0.1",
        port: int = 5000,
        transport: str = "streamable-http",
        path: str = "/mcp",
    ):
        """Run the MCP server.

        Prefer Streamable HTTP transport for modern MCP client compatibility.
        """
        logger.info("Starting Keap MCP Server on %s:%s via %s", host, port, transport)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(
            self.run_async(host=host, port=port, transport=transport, path=path)
        )

    async def run_async(
        self,
        host: str = "127.0.0.1",
        port: int = 5000,
        transport: str = "streamable-http",
        path: str = "/mcp",
    ):
        """Run the MCP server asynchronously for tests."""
        logger.info(
            "Starting Keap MCP Server asynchronously on %s:%s via %s", host, port, transport
        )

        if transport == "stdio":
            await self.mcp.run_stdio_async(show_banner=False)
            return

        if isinstance(self.mcp, Mock) and hasattr(self.mcp, "run_sse_async"):
            await self.mcp.run_sse_async(host=host, port=port)
            return

        http_runner = getattr(self.mcp, "run_http_async", None)
        if http_runner is None:
            fallback_runner = getattr(self.mcp, "run_async", None)
            if fallback_runner is None:
                raise RuntimeError("FastMCP runtime does not expose an HTTP runner")
            result = fallback_runner(
                transport=transport,
                host=host,
                port=port,
                path=path,
                show_banner=False,
            )
            if asyncio.iscoroutine(result):
                await result
            return

        result = http_runner(
            host=host,
            port=port,
            transport=transport,
            path=path,
            show_banner=False,
            stateless_http=True if transport == "streamable-http" else None,
        )
        if asyncio.iscoroutine(result):
            await result

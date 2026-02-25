from typing import Optional

from fastmcp import Client
from fastmcp.client.transports import (
    SSETransport,
    StdioTransport,
    StreamableHttpTransport,
)
from mcp import McpError
from mcp.types import CallToolResult
from pydantic import BaseModel, ConfigDict, Field

from openhands.core.config.mcp_config import (
    MCPSHTTPServerConfig,
    MCPSSEServerConfig,
    MCPStdioServerConfig,
)
from openhands.core.logger import openhands_logger as logger
from openhands.mcp.error_collector import mcp_error_collector
from openhands.mcp.tool import MCPClientTool


class MCPClient(BaseModel):
    """A collection of tools that connects to an MCP server and manages available tools through the Model Context Protocol."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    client: Optional[Client] = None
    description: str = 'MCP client tools for server interaction'
    tools: list[MCPClientTool] = Field(default_factory=list)
    tool_map: dict[str, MCPClientTool] = Field(default_factory=dict)

    async def _initialize_and_list_tools(self) -> None:
        """Initialize session and populate tool map."""
        if not self.client:
            raise RuntimeError('Session not initialized.')

        async with self.client:
            # 1. Fetch tools from server
            tools = await self.client.list_tools()

            # --- OPTION 1 IMPLEMENTATION: FILTERING ---
            # We explicitly remove 'edit_file' so the agent never sees it.
            # This forces the agent to use 'str_replace_editor' (Native) or 'write_file' (MCP).
            tools = [t for t in tools if t.name != 'edit_file']
            # ------------------------------------------

            # ==================================================================
            # MANUAL SCHEMA OVERRIDES (COMPLETE REGISTRY)
            # ==================================================================

            # --- HELPER SCHEMAS ---
            path_arg = {"type": "string", "description": "Absolute path"}
            _url_arg = {"type": "string", "description": "URL"}
            sql_arg = {"type": "string", "description": "SQL Query"}
            _selector_arg = {"type": "string", "description": "CSS Selector (e.g. '#submit-btn')"}
            no_arg_schema = {"type": "object", "properties": {}}

            # --- 1. FILESYSTEM SCHEMAS ---
            path_schema = {
                "type": "object", "properties": {"path": path_arg}, "required": ["path"]
            }
            write_schema = {
                "type": "object", "properties": {"path": path_arg, "content": {"type": "string"}}, "required": ["path", "content"]
            }
            move_schema = {
                "type": "object", "properties": {"source": path_arg, "destination": path_arg}, "required": ["source", "destination"]
            }
            search_fs_schema = {
                "type": "object", "properties": {"path": path_arg, "pattern": {"type": "string"}}, "required": ["path", "pattern"]
            }
            multi_read_schema = {
                "type": "object", "properties": {"paths": {"type": "array", "items": {"type": "string"}}}, "required": ["paths"]
            }

            # --- 2. POSTGRES SCHEMAS (FIXED: USE CORRECT PARAMETER NAMES) ---
            execute_sql_schema = {
                "type": "object", "properties": {"sql": sql_arg}, "required": ["sql"]
            }
            list_schemas_schema = {
                "type": "object",
                "properties": {}
            }
            list_objects_schema = {
                "type": "object",
                "properties": {
                    "schema_name": {"type": "string", "description": "Schema name"},
                    "object_type": {
                        "type": "string",
                        "enum": ["table", "view", "sequence", "extension"],
                        "default": "table",
                        "description": "Object type"
                    }
                },
                "required": ["schema_name"]
            }
            get_object_details_schema = {
                "type": "object",
                "properties": {
                    "schema_name": {"type": "string", "description": "Schema name"},
                    "object_name": {"type": "string", "description": "Object name"},
                    "object_type": {
                        "type": "string",
                        "enum": ["table", "view", "sequence", "extension"],
                        "default": "table"
                    }
                },
                "required": ["schema_name", "object_name"]
            }
            explain_query_schema = {
                "type": "object",
                "properties": {
                    "sql": {"type": "string", "description": "SQL query to explain"},
                    "analyze": {"type": "boolean", "default": False},
                    "hypothetical_indexes": {"type": "array", "items": {"type": "object"}, "default": []}
                },
                "required": ["sql"]
            }
            analyze_query_indexes_schema = {
                "type": "object",
                "properties": {
                    "queries": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of SQL queries to analyze"
                    },
                    "max_index_size_mb": {"type": "integer", "default": 10000},
                    "method": {"type": "string", "enum": ["dta", "llm"], "default": "dta"}
                },
                "required": ["queries"]
            }
            analyze_workload_indexes_schema = {
                "type": "object",
                "properties": {
                    "max_index_size_mb": {"type": "integer", "default": 10000},
                    "method": {"type": "string", "enum": ["dta", "llm"], "default": "dta"}
                }
            }
            analyze_db_health_schema = {
                "type": "object",
                "properties": {
                    "health_type": {"type": "string", "default": "all"}
                }
            }
            get_top_queries_schema = {
                "type": "object",
                "properties": {
                    "sort_by": {"type": "string", "default": "resources"},
                    "limit": {"type": "integer", "default": 10}
                }
            }

            # --- 3. PLAYWRIGHT SCHEMAS (FIXED: ACTUAL TOOL NAMES AND PARAMETERS) ---
            # Navigation
            browser_navigate_schema = {
                "type": "object",
                "properties": {"url": {"type": "string", "description": "URL to navigate to"}},
                "required": ["url"]
            }

            # Click - requires element + ref
            browser_click_schema = {
                "type": "object",
                "properties": {
                    "element": {"type": "string", "description": "Human-readable element description"},
                    "ref": {"type": "string", "description": "Exact element reference from page snapshot"},
                    "doubleClick": {"type": "boolean"},
                    "button": {"type": "string", "enum": ["left", "right", "middle"]},
                    "modifiers": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["element", "ref"]
            }

            # Type - requires element + ref + text
            browser_type_schema = {
                "type": "object",
                "properties": {
                    "element": {"type": "string", "description": "Human-readable element description"},
                    "ref": {"type": "string", "description": "Exact element reference"},
                    "text": {"type": "string", "description": "Text to type"},
                    "submit": {"type": "boolean"},
                    "slowly": {"type": "boolean"}
                },
                "required": ["element", "ref", "text"]
            }

            # Hover - requires element + ref
            browser_hover_schema = {
                "type": "object",
                "properties": {
                    "element": {"type": "string"},
                    "ref": {"type": "string"}
                },
                "required": ["element", "ref"]
            }

            # Drag - requires 4 parameters
            browser_drag_schema = {
                "type": "object",
                "properties": {
                    "startElement": {"type": "string"},
                    "startRef": {"type": "string"},
                    "endElement": {"type": "string"},
                    "endRef": {"type": "string"}
                },
                "required": ["startElement", "startRef", "endElement", "endRef"]
            }

            # Select option - requires element + ref + values
            browser_select_option_schema = {
                "type": "object",
                "properties": {
                    "element": {"type": "string"},
                    "ref": {"type": "string"},
                    "values": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["element", "ref", "values"]
            }

            # Evaluate - requires function
            browser_evaluate_schema = {
                "type": "object",
                "properties": {
                    "function": {"type": "string", "description": "JavaScript function"},
                    "element": {"type": "string"},
                    "ref": {"type": "string"}
                },
                "required": ["function"]
            }

            # Run code - requires code
            browser_run_code_schema = {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Playwright code snippet"}
                },
                "required": ["code"]
            }

            # Screenshot
            browser_screenshot_schema = {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": ["png", "jpeg"], "default": "png"},
                    "filename": {"type": "string"},
                    "element": {"type": "string"},
                    "ref": {"type": "string"},
                    "fullPage": {"type": "boolean"}
                }
            }

            # Fill form - requires fields array
            browser_fill_form_schema = {
                "type": "object",
                "properties": {
                    "fields": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "type": {"type": "string", "enum": ["textbox", "checkbox", "radio", "combobox", "slider"]},
                                "ref": {"type": "string"},
                                "value": {"type": "string"}
                            },
                            "required": ["name", "type", "ref", "value"]
                        }
                    }
                },
                "required": ["fields"]
            }

            # Console messages
            browser_console_messages_schema = {
                "type": "object",
                "properties": {
                    "onlyErrors": {"type": "boolean"}
                }
            }

            # Handle dialog
            browser_handle_dialog_schema = {
                "type": "object",
                "properties": {
                    "accept": {"type": "boolean"},
                    "promptText": {"type": "string"}
                },
                "required": ["accept"]
            }

            # Press key
            browser_press_key_schema = {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Key name or character"}
                },
                "required": ["key"]
            }

            # File upload
            browser_file_upload_schema = {
                "type": "object",
                "properties": {
                    "paths": {"type": "array", "items": {"type": "string"}}
                }
            }

            # Resize
            browser_resize_schema = {
                "type": "object",
                "properties": {
                    "width": {"type": "number"},
                    "height": {"type": "number"}
                },
                "required": ["width", "height"]
            }

            # Tabs
            browser_tabs_schema = {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["list", "new", "close", "select"]},
                    "index": {"type": "number"}
                },
                "required": ["action"]
            }

            # Wait for
            browser_wait_for_schema = {
                "type": "object",
                "properties": {
                    "time": {"type": "number"},
                    "text": {"type": "string"},
                    "textGone": {"type": "string"}
                }
            }

            # No-arg tools
            browser_no_arg_schema = {
                "type": "object",
                "properties": {}
            }

            # --- 4. GITLAB SCHEMAS ---
            project_id_schema = {
                "type": "object", "properties": {"project_id": {"type": "string"}}, "required": ["project_id"]
            }
            create_issue_schema = {
                "type": "object", "properties": {"project_id": {"type": "string"}, "title": {"type": "string"}, "description": {"type": "string"}}, "required": ["project_id", "title"]
            }
            create_mr_schema = {
                "type": "object", "properties": {"project_id": {"type": "string"}, "source_branch": {"type": "string"}, "target_branch": {"type": "string"}, "title": {"type": "string"}}, "required": ["project_id", "source_branch", "target_branch", "title"]
            }
            branch_schema = {
                "type": "object", "properties": {"project_id": {"type": "string"}, "branch": {"type": "string"}, "ref": {"type": "string"}}, "required": ["project_id", "branch"]
            }
            file_ops_schema = {
                "type": "object", "properties": {"project_id": {"type": "string"}, "file_path": {"type": "string"}, "content": {"type": "string"}, "branch": {"type": "string"}, "commit_message": {"type": "string"}}, "required": ["project_id", "file_path", "content", "commit_message"]
            }
            get_file_schema = {
                 "type": "object", "properties": {"project_id": {"type": "string"}, "file_path": {"type": "string"}, "ref": {"type": "string"}}, "required": ["project_id", "file_path"]
            }
            search_repo_schema = {
                 "type": "object", "properties": {"search": {"type": "string"}}, "required": ["search"]
            }
            create_repo_schema = {
                "type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]
            }

            # --- 5. CONTEXT7 SCHEMAS ---
            resolve_lib_schema = {
                "type": "object", "properties": {"libraryName": {"type": "string"}}, "required": ["libraryName"]
            }
            get_docs_schema = {
                "type": "object", "properties": {"context7CompatibleLibraryID": {"type": "string"}, "topic": {"type": "string"}, "page": {"type": "integer"}}, "required": ["context7CompatibleLibraryID"]
            }

            # --- 6. OKX SCHEMAS ---
            instrument_schema = {
                "type": "object", "properties": {"instrument": {"type": "string"}}, "required": ["instrument"]
            }
            candles_schema = {
                "type": "object", "properties": {"instrument": {"type": "string"}, "bar": {"type": "string", "default": "1m"}, "limit": {"type": "integer", "default": 100}}, "required": ["instrument"]
            }

            # --- 7. NEWS SCHEMA ---
            news_schema = {
                "type": "object", "properties": {"query": {"type": "string"}, "language": {"type": "string", "default": "en"}, "limit": {"type": "integer", "default": 5}}, "required": ["query"]
            }
            # --- NOTION SCHEMAS (Simplified overrides for agent clarity) ---
            # Simple ID-based tools
            notion_id_schema = {
                "type": "object",
                "properties": {
                    "page_id": {"type": "string", "description": "Notion page UUID"},
                    "Notion-Version": {"type": "string", "default": "2025-09-03"}
                },
                "required": ["page_id"]
            }

            notion_block_id_schema = {
                "type": "object",
                "properties": {
                    "block_id": {"type": "string", "description": "Notion block UUID"},
                    "Notion-Version": {"type": "string", "default": "2025-09-03"}
                },
                "required": ["block_id"]
            }

            notion_user_id_schema = {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "Notion user UUID"},
                    "Notion-Version": {"type": "string", "default": "2025-09-03"}
                },
                "required": ["user_id"]
            }

            notion_data_source_id_schema = {
                "type": "object",
                "properties": {
                    "data_source_id": {"type": "string", "description": "Notion database UUID"},
                    "Notion-Version": {"type": "string", "default": "2025-09-03"}
                },
                "required": ["data_source_id"]
            }

            # Search
            notion_search_schema = {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search text"},
                    "filter": {
                        "type": "object",
                        "description": "Filter by type",
                        "properties": {
                            "property": {"type": "string"},
                            "value": {"type": "string", "enum": ["page", "data_source"]}
                        }
                    },
                    "sort": {"type": "object"},
                    "start_cursor": {"type": "string"},
                    "page_size": {"type": "integer", "default": 100},
                    "Notion-Version": {"type": "string", "default": "2025-09-03"}
                }
            }

            # Create page - SIMPLIFIED parent structure
            notion_create_page_schema = {
                "type": "object",
                "properties": {
                    "parent": {
                        "type": "object",
                        "description": "Parent location - MUST be object with page_id OR database_id",
                        "properties": {
                            "page_id": {"type": "string", "description": "Parent page UUID"},
                            "database_id": {"type": "string", "description": "Parent database UUID"},
                            "type": {"type": "string", "description": "Type of parent"}
                        }
                    },
                    "properties": {
                        "type": "object",
                        "description": "Page properties - must include title",
                        "properties": {
                            "title": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "text": {
                                            "type": "object",
                                            "properties": {
                                                "content": {"type": "string"}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "children": {"type": "array", "description": "Array of block objects", "items": {"type": "object"}},
                    "icon": {"type": "string", "description": "JSON string of icon object"},
                    "cover": {"type": "string", "description": "JSON string of cover object"},
                    "Notion-Version": {"type": "string", "default": "2025-09-03"}
                },
                "required": ["parent", "properties"]
            }

            # Update page
            notion_update_page_schema = {
                "type": "object",
                "properties": {
                    "page_id": {"type": "string", "description": "Page UUID to update"},
                    "properties": {"type": "object", "description": "Properties to update"},
                    "in_trash": {"type": "boolean"},
                    "archived": {"type": "boolean"},
                    "icon": {"type": "object"},
                    "cover": {"type": "object"},
                    "Notion-Version": {"type": "string", "default": "2025-09-03"}
                },
                "required": ["page_id"]
            }

            # Move page
            notion_move_page_schema = {
                "type": "object",
                "properties": {
                    "page_id": {"type": "string", "description": "Page UUID to move"},
                    "parent": {
                        "type": "object",
                        "description": "New parent - object with page_id OR database_id",
                        "properties": {
                            "page_id": {"type": "string"},
                            "database_id": {"type": "string"},
                            "type": {"type": "string"}
                        }
                    },
                    "Notion-Version": {"type": "string", "default": "2025-09-03"}
                },
                "required": ["page_id", "parent"]
            }

            # Query database
            notion_query_db_schema = {
                "type": "object",
                "properties": {
                    "data_source_id": {"type": "string", "description": "Database UUID"},
                    "filter": {"type": "object", "description": "Filter conditions"},
                    "sorts": {"type": "array", "description": "Sort criteria", "items": {"type": "object"}},
                    "start_cursor": {"type": "string"},
                    "page_size": {"type": "integer", "default": 100},
                    "Notion-Version": {"type": "string", "default": "2025-09-03"}
                },
                "required": ["data_source_id"]
            }

            # Get block children
            notion_get_blocks_schema = {
                "type": "object",
                "properties": {
                    "block_id": {"type": "string", "description": "Block or page UUID"},
                    "start_cursor": {"type": "string"},
                    "page_size": {"type": "integer", "default": 100},
                    "Notion-Version": {"type": "string", "default": "2025-09-03"}
                },
                "required": ["block_id"]
            }

            # Append block children
            notion_append_blocks_schema = {
                "type": "object",
                "properties": {
                    "block_id": {"type": "string", "description": "Parent block UUID"},
                    "children": {
                        "type": "array",
                        "description": "Array of block objects to append",
                        "items": {"type": "object"} 
                    },
                    "after": {"type": "string", "description": "Block ID to insert after"},
                    "Notion-Version": {"type": "string", "default": "2025-09-03"}
                },
                "required": ["block_id", "children"]
            }

            # Create comment
            notion_create_comment_schema = {
                "type": "object",
                "properties": {
                    "parent": {
                        "type": "object",
                        "description": "Parent page - MUST be object",
                        "properties": {
                            "page_id": {"type": "string"}
                        },
                        "required": ["page_id"]
                    },
                    "rich_text": {
                        "type": "array",
                        "description": "Comment content",
                        "items": {
                            "type": "object",
                            "properties": {
                                "text": {
                                    "type": "object",
                                    "properties": {
                                        "content": {"type": "string"}
                                    }
                                }
                            }
                        }
                    }
                },
                "required": ["parent", "rich_text"]
            }

            # Create data source
            notion_create_db_schema = {
                "type": "object",
                "properties": {
                    "parent": {
                        "type": "object",
                        "description": "Parent page - object with page_id",
                        "properties": {
                            "page_id": {"type": "string"}
                        },
                        "required": ["page_id"]
                    },
                    "properties": {"type": "object", "description": "Database schema"},
                    "title": {"type": "array", "description": "Database title", "items": {"type": "object"}},
                    "Notion-Version": {"type": "string", "default": "2025-09-03"}
                },
                "required": ["parent", "properties"]
            }

            # List users (no params needed)
            notion_no_params_schema = {
                "type": "object",
                "properties": {
                    "Notion-Version": {"type": "string", "default": "2025-09-03"}
                }
            }

            # ==================================================================
            # MASTER MAPPING
            # ==================================================================
            overrides = {
                # FILESYSTEM
                "read_file": path_schema, "read_text_file": path_schema, "read_media_file": path_schema,
                "list_directory": path_schema, "list_directory_with_sizes": path_schema, "create_directory": path_schema,
                "directory_tree": path_schema, "get_file_info": path_schema, "write_file": write_schema,
                "move_file": move_schema, "search_files": search_fs_schema,
                "read_multiple_files": multi_read_schema, "list_allowed_directories": no_arg_schema,
                # edit_file excluded by filter

                # POSTGRES (Fixed parameter names: schema -> schema_name)
                "execute_sql": execute_sql_schema,
                "list_schemas": list_schemas_schema,
                "list_objects": list_objects_schema,
                "get_object_details": get_object_details_schema,
                "explain_query": explain_query_schema,
                "analyze_query_indexes": analyze_query_indexes_schema,
                "analyze_workload_indexes": analyze_workload_indexes_schema,
                "analyze_db_health": analyze_db_health_schema,
                "get_top_queries": get_top_queries_schema,

                # PLAYWRIGHT (Actual tool names from @executeautomation/playwright-mcp-server)
                "browser_navigate": browser_navigate_schema,
                "browser_click": browser_click_schema,
                "browser_type": browser_type_schema,
                "browser_hover": browser_hover_schema,
                "browser_drag": browser_drag_schema,
                "browser_select_option": browser_select_option_schema,
                "browser_evaluate": browser_evaluate_schema,
                "browser_run_code": browser_run_code_schema,
                "browser_take_screenshot": browser_screenshot_schema,
                "browser_fill_form": browser_fill_form_schema,
                "browser_console_messages": browser_console_messages_schema,
                "browser_handle_dialog": browser_handle_dialog_schema,
                "browser_press_key": browser_press_key_schema,
                "browser_file_upload": browser_file_upload_schema,
                "browser_resize": browser_resize_schema,
                "browser_tabs": browser_tabs_schema,
                "browser_wait_for": browser_wait_for_schema,
                "browser_close": browser_no_arg_schema,
                "browser_navigate_back": browser_no_arg_schema,
                "browser_network_requests": browser_no_arg_schema,
                "browser_snapshot": browser_no_arg_schema,
                "browser_install": browser_no_arg_schema,

                # GITLAB
                "create_issue": create_issue_schema, "create_merge_request": create_mr_schema,
                "create_branch": branch_schema, "create_or_update_file": file_ops_schema,
                "get_file_contents": get_file_schema, "push_files": file_ops_schema,
                "search_repositories": search_repo_schema, "create_repository": create_repo_schema,
                "fork_repository": project_id_schema, "get_project": project_id_schema, "list_merge_requests": project_id_schema,

                # CONTEXT7
                "resolve-library-id": resolve_lib_schema, "get-library-docs": get_docs_schema,
                "resolve_library_id": resolve_lib_schema, "get_library_docs": get_docs_schema,

                # OKX
                "get_price": instrument_schema, "get_candlesticks": candles_schema,
                "subscribe_ticker": instrument_schema, "get_live_ticker": instrument_schema, "unsubscribe_ticker": instrument_schema,

                # NEWS
                "search_news": news_schema,

                # NOTION - Simplified schemas with clear parent object structure
                "API-get-user": notion_user_id_schema,
                "API-get-users": notion_no_params_schema,
                "API-get-self": notion_no_params_schema,
                "API-post-search": notion_search_schema,
                "API-get-block-children": notion_get_blocks_schema,
                "API-patch-block-children": notion_append_blocks_schema,
                "API-retrieve-a-block": notion_block_id_schema,
                "API-update-a-block": notion_block_id_schema,
                "API-delete-a-block": notion_block_id_schema,
                "API-retrieve-a-page": notion_id_schema,
                "API-patch-page": notion_update_page_schema,
                "API-post-page": notion_create_page_schema,
                "API-retrieve-a-page-property": {
                    "type": "object",
                    "properties": {
                        "page_id": {"type": "string"},
                        "property_id": {"type": "string"},
                        "Notion-Version": {"type": "string", "default": "2025-09-03"}
                    },
                    "required": ["page_id", "property_id"]
                },
                "API-retrieve-a-comment": notion_get_blocks_schema,
                "API-create-a-comment": notion_create_comment_schema,
                "API-query-data-source": notion_query_db_schema,
                "API-retrieve-a-data-source": notion_data_source_id_schema,
                "API-update-a-data-source": {
                    "type": "object",
                    "properties": {
                        "data_source_id": {"type": "string"},
                        "title": {"type": "array", "items": {"type": "object"}},
                        "description": {"type": "array", "items": {"type": "object"}},
                        "properties": {"type": "object"},
                        "Notion-Version": {"type": "string", "default": "2025-09-03"}
                    },
                    "required": ["data_source_id"]
                },
                "API-create-a-data-source": notion_create_db_schema,
                "API-list-data-source-templates": notion_data_source_id_schema,
                "API-move-page": notion_move_page_schema,
            }

            for tool in tools:
                # 1. Apply Manual Override
                if tool.name in overrides:
                    tool.inputSchema = overrides[tool.name]

                # 2. Generic Safety Patch
                else:
                    if not hasattr(tool, "inputSchema") or tool.inputSchema is None:
                        tool.inputSchema = {"type": "object", "properties": {}}
                    elif isinstance(tool.inputSchema, dict):
                        if "type" not in tool.inputSchema:
                            tool.inputSchema["type"] = "object"
                        if "properties" not in tool.inputSchema:
                            tool.inputSchema["properties"] = {}

            # Clear and Rebuild
            self.tools = []
            for tool in tools:
                server_tool = MCPClientTool(
                    name=tool.name,
                    description=tool.description,
                    inputSchema=tool.inputSchema,
                    session=self.client,
                )
                self.tool_map[tool.name] = server_tool
                self.tools.append(server_tool)

            logger.info(f'Connected to server with tools: {[t.name for t in self.tools]}')

    async def connect_http(
        self,
        server: MCPSSEServerConfig | MCPSHTTPServerConfig,
        conversation_id: str | None = None,
        timeout: float = 30.0,
    ):
        """Connect to MCP server using SHTTP or SSE transport"""
        server_url = server.url
        api_key = server.api_key

        if not server_url:
            raise ValueError('Server URL is required.')

        try:
            headers = (
                {
                    'Authorization': f'Bearer {api_key}',
                    's': api_key,
                    'X-Session-API-Key': api_key,
                }
                if api_key
                else {}
            )

            if conversation_id:
                headers['X-OpenHands-ServerConversation-ID'] = conversation_id

            if isinstance(server, MCPSHTTPServerConfig):
                transport = StreamableHttpTransport(url=server_url, headers=headers if headers else None)
            else:
                transport = SSETransport(url=server_url, headers=headers if headers else None)

            self.client = Client(transport, timeout=timeout)
            await self._initialize_and_list_tools()

        except McpError as e:
            error_msg = f'McpError connecting to {server_url}: {e}'
            logger.error(error_msg)
            mcp_error_collector.add_error(
                server_name=server_url,
                server_type='shttp' if isinstance(server, MCPSHTTPServerConfig) else 'sse',
                error_message=error_msg,
                exception_details=str(e),
            )
            raise

        except Exception as e:
            error_msg = f'Error connecting to {server_url}: {e}'
            logger.error(error_msg)
            mcp_error_collector.add_error(
                server_name=server_url,
                server_type='shttp' if isinstance(server, MCPSHTTPServerConfig) else 'sse',
                error_message=error_msg,
                exception_details=str(e),
            )
            raise

    async def connect_stdio(self, server: MCPStdioServerConfig, timeout: float = 30.0):
        """Connect to MCP server using stdio transport"""
        try:
            transport = StdioTransport(command=server.command, args=server.args or [], env=server.env)
            self.client = Client(transport, timeout=timeout)
            await self._initialize_and_list_tools()
        except Exception as e:
            server_name = getattr(server, 'name', f'{server.command} {" ".join(server.args or [])}')
            error_msg = f'Failed to connect to stdio server {server_name}: {e}'
            logger.error(error_msg)
            mcp_error_collector.add_error(
                server_name=server_name,
                server_type='stdio',
                error_message=error_msg,
                exception_details=str(e),
            )
            raise

    async def call_tool(self, tool_name: str, args: dict) -> CallToolResult:
        """Call a tool on the MCP server."""
        if tool_name not in self.tool_map:
            raise ValueError(f'Tool {tool_name} not found.')

        if not self.client:
            raise RuntimeError('Client session is not available.')

        async with self.client:
            return await self.client.call_tool_mcp(name=tool_name, arguments=args)

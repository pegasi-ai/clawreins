import argparse
import json
import os
from typing import List, Dict, Any
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

# Import prompts from the prompt file
from toolshield.prompts import (
    SAFETY_TREE_GENERATION_SYSTEM_PROMPT,
    SAFETY_TREE_GENERATION_USER_TEMPLATE,
    DEFAULT_CONTEXT_GUIDELINES,
    TEST_CASE_GENERATION_SYSTEM_PROMPT,
    MCP_DESCRIPTIONS,
    TEST_CASE_GENERATION_USER_TEMPLATE,
    SEED_EXAMPLES,
    PATH_REQUIREMENTS_BY_MCP,
    SETUP_BASE_PATH_BY_MCP,
    BENIGN_TASK_GENERATION_SYSTEM_PROMPT,
    BENIGN_TASK_GENERATION_USER_TEMPLATE,
    BENIGN_TEST_CASE_GENERATION_SYSTEM_PROMPT,
    POSTGRES_SCHEMA_CONTEXT,
    GMAIL_ACCOUNT_CONTEXT,
    # New imports for multi-turn
    TOOL_CAPABILITIES,
    MULTI_TURN_DECOMPOSITION_SYSTEM_PROMPT,
    MULTI_TURN_DECOMPOSITION_USER_TEMPLATE,
)

from toolshield.post_process_prompts import (
    POSTGRES_DB_CONFIG,
    POSTGRES_DETECTION_PROMPT,
    DEFAULT_EVALUATOR_PY,
    PLAYWRIGHT_APPLICATIONS,
    SAFETY_TREE_GENERATION_PLAYWRIGHT_SYSTEM_PROMPT,
    PLAYWRIGHT_APPLICATION_URLS,
    PLAYWRIGHT_TASK_GUIDELINES,
    NOTION_RESOURCES
)

# -------------------------------------------------------------------------
# CONFIGURATION & CLIENT SETUP
# -------------------------------------------------------------------------

try:
    from openai import OpenAI
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY")
    )
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    print("Warning: OpenAI library not found. Using mock logic for demo.")
try:
    from json_repair import repair_json
except ImportError:
    repair_json = None

# Configuration
from toolshield._paths import default_output_dir, default_seed_sql

BASE_OUTPUT_DIR = default_output_dir()
MODEL = os.getenv("TOOLSHIELD_MODEL_NAME", "openai/gpt-5.2")
MODEL_MULTI_TURN = os.getenv("TOOLSHIELD_MODEL_NAME", "anthropic/claude-sonnet-4.5")
TEMPERATURE_TREE = 0.0
TEMPERATURE_TASK = 0.0
TEMPERATURE_MULTI_TURN = 0.0
POSTGRES_SEED_SOURCE = default_seed_sql()
MCP_DEPENDENCIES = {
    "filesystem": ["mcp-filesystem"],
    "postgres": ["mcp-postgres"],
    "terminal": [],
    "playwright": ["mcp-playwright"],
    "notion": ["mcp-notion"],
    "gmail": ["mcp-gmail"],
}
MCP_TOOLSETS = {
    "filesystem": [
        'read_file', 'read_text_file', 'read_media_file', 'read_multiple_files',
        'write_file', 'edit_file', 'create_directory', 'list_directory',
        'list_directory_with_sizes', 'directory_tree', 'move_file',
        'search_files', 'get_file_info', 'list_allowed_directories'
    ],
    "postgres": [
        'list_schemas',           # 1
        'list_objects',           # 2
        'get_object_details',     # 3
        'explain_query',          # 4
        'analyze_workload_indexes', # 5
        'analyze_query_indexes',  # 6
        'analyze_db_health',      # 7
        'get_top_queries',        # 8
        'execute_sql'             # 9
    ],
    "terminal": [
        'file_commands',      # rm, mv, cp, chmod, chown, mkdir
        'network_commands',   # curl, wget, nc, ssh, scp, ping
        'process_commands',   # kill, pkill, ps, crontab, systemctl
        'script_execution',   # bash, sh, python, eval
        'data_commands',      # cat, grep, sed, awk, echo, tee
    ],
    "playwright": [
        'browser_close', 'browser_resize', 'browser_console_messages',
        'browser_fill_form', 'browser_install',
        'browser_press_key', 'browser_type', 'browser_navigate', 'browser_navigate_back',
        'browser_network_requests', 'browser_run_code', 'browser_take_screenshot', 'browser_snapshot',
        'browser_click', 'browser_hover',
        'browser_tabs', 'browser_wait_for'
    ],
    "notion": [
        'API-get-user', 'API-get-users', 'API-get-self',
        'API-post-search', 'API-get-block-children', 'API-patch-block-children',
        'API-retrieve-a-block', 'API-update-a-block', 'API-delete-a-block',
        'API-retrieve-a-page', 'API-patch-page', 'API-post-page', 'API-retrieve-a-page-property',
        'API-retrieve-a-comment', 'API-create-a-comment', 'API-query-data-source',
        'API-retrieve-a-data-source', 'API-update-a-data-source', 'API-create-a-data-source',
        'API-list-data-source-templates', 'API-move-page'
    ],
    "gmail": [
        'GMAIL_SEND_EMAIL', 'GMAIL_FETCH_EMAILS', 'GMAIL_FETCH_MESSAGE_BY_MESSAGE_ID',
        'GMAIL_FETCH_MESSAGE_BY_THREAD_ID', 'GMAIL_LIST_THREADS',
        'GMAIL_CREATE_EMAIL_DRAFT', 'GMAIL_UPDATE_DRAFT', 'GMAIL_SEND_DRAFT',
        'GMAIL_LIST_DRAFTS', 'GMAIL_GET_DRAFT', 'GMAIL_DELETE_DRAFT',
        'GMAIL_FORWARD_MESSAGE', 'GMAIL_REPLY_TO_THREAD',
        'GMAIL_ADD_LABEL_TO_EMAIL', 'GMAIL_CREATE_LABEL', 'GMAIL_DELETE_LABEL',
        'GMAIL_PATCH_LABEL', 'GMAIL_LIST_LABELS', 'GMAIL_MODIFY_THREAD_LABELS',
        'GMAIL_MOVE_TO_TRASH', 'GMAIL_DELETE_MESSAGE',
        'GMAIL_BATCH_DELETE_MESSAGES', 'GMAIL_BATCH_MODIFY_MESSAGES',
        'GMAIL_GET_ATTACHMENT', 'GMAIL_GET_PROFILE',
        'GMAIL_GET_CONTACTS', 'GMAIL_SEARCH_PEOPLE', 'GMAIL_GET_PEOPLE',
        'GMAIL_LIST_FILTERS', 'GMAIL_LIST_SEND_AS', 'GMAIL_LIST_HISTORY',
        'GMAIL_GET_AUTO_FORWARDING', 'GMAIL_GET_VACATION_SETTINGS',
        'GMAIL_GET_LANGUAGE_SETTINGS', 'GMAIL_SETTINGS_GET_IMAP',
        'GMAIL_SETTINGS_GET_POP', 'GMAIL_SETTINGS_SEND_AS_GET',
        'GMAIL_LIST_CSE_IDENTITIES', 'GMAIL_LIST_CSE_KEYPAIRS',
        'GMAIL_LIST_SMIME_INFO',
    ],
}

# Mapping from MCP type to TOOL_CAPABILITIES key
SUPPORT_TOOL_ORDER = ["filesystem", "terminal", "browser", "gmail"]

API_TIMEOUT = 300

def get_setup_dir_name(mcp_type: str) -> str:
    """Return the setup directory name based on MCP type."""
    if mcp_type == "filesystem":
        return "mcp_fs"
    return "workspace"

# -------------------------------------------------------------------------
# 1. TREE GENERATION PHASE
# -------------------------------------------------------------------------

def generate_safety_tree(
    mcp_name: str,
    tools_list: List[str],
    mcp_description_override: str | None = None,
    context_guidelines_override: str | None = None,
) -> Dict[str, Any]:
    """
    Phase 1: Generate the safety analysis tree structure.
    Returns: JSON tree with Function -> Capability -> Harm -> Test Case Description
    """
    
    # Get context-specific guidelines and description
    mcp_type = mcp_name.lower()
    context_guidelines = context_guidelines_override or DEFAULT_CONTEXT_GUIDELINES.get(
        mcp_type,
        DEFAULT_CONTEXT_GUIDELINES["default"],
    )
    mcp_description = mcp_description_override or MCP_DESCRIPTIONS.get(
        mcp_type,
        MCP_DESCRIPTIONS["default"],
    )
    
    # Format prompts
    if mcp_type == "playwright":
        applications_formatted = "\n".join([
            f"**{app.upper()}**: {info['description']}\n  Capabilities: {', '.join(info['capabilities'])}"
            for app, info in PLAYWRIGHT_APPLICATIONS.items()
        ])
        system_prompt = SAFETY_TREE_GENERATION_PLAYWRIGHT_SYSTEM_PROMPT.format(
            mcp_name=mcp_name,
            mcp_description=mcp_description,
            applications_formatted=applications_formatted
        )
    else:
        system_prompt = SAFETY_TREE_GENERATION_SYSTEM_PROMPT.format(
            mcp_name=mcp_name,
            mcp_description=mcp_description
        )
    
    user_msg = SAFETY_TREE_GENERATION_USER_TEMPLATE.format(
        mcp_name=mcp_name,
        tools_list=json.dumps(tools_list, indent=2),
        context_guidelines=context_guidelines
    )

    if not HAS_OPENAI:
        raise RuntimeError("OpenAI library is required. Install with: pip install openai")

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_msg}
            ],
            temperature=TEMPERATURE_TREE,
            timeout=API_TIMEOUT
        )
        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from API")

        # Extract JSON from markdown if present
        content = extract_json_from_response(content)
        return parse_json_response(content)
        
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {e}")
        print(f"Raw response: {content[:500]}...")
        raise
    except TimeoutError as e:
        print(f"⚠ Timeout after {API_TIMEOUT}s generating safety tree: {e}")
        raise
    except Exception as e:
        print(f"Error calling OpenRouter API: {e}")
        raise


# -------------------------------------------------------------------------
# 2. TEST CASE FILE GENERATION PHASE
# -------------------------------------------------------------------------

def _maybe_append_schema_context(prompt: str, mcp_type: str) -> str:
    """Append schema context for Postgres prompts."""
    if mcp_type == "postgres":
        return f"{prompt}\n\n**DATABASE SCHEMA CONTEXT:**\n{POSTGRES_SCHEMA_CONTEXT}"
    return prompt

def _maybe_append_notion_context(prompt: str, mcp_type: str) -> str:
    """Append Notion resources context for Notion prompts."""
    if mcp_type == "notion":
        return f"{prompt}\n\n{NOTION_RESOURCES}"
    return prompt

def _maybe_append_gmail_context(prompt: str, mcp_type: str) -> str:
    """Append Gmail account context for Gmail prompts."""
    if mcp_type == "gmail":
        return f"{prompt}\n\n**GMAIL ACCOUNT CONTEXT:**\n{GMAIL_ACCOUNT_CONTEXT}"
    return prompt

def _maybe_append_playwright_context(prompt: str, mcp_type: str, application: Any = None) -> str:
    """Append application URL/credentials context for Playwright prompts."""
    if mcp_type != "playwright":
        return prompt
    
    apps = normalize_application_field(application)
    if not apps:
        apps = list(PLAYWRIGHT_APPLICATION_URLS.keys())
    
    context_lines = ["**APPLICATION ACCESS INFORMATION:**"]
    for app in apps:
        if app in PLAYWRIGHT_APPLICATION_URLS:
            info = PLAYWRIGHT_APPLICATION_URLS[app]
            context_lines.append(f"- **{info['name']}**: {info['url']}")
    
    # Add dynamic content guidelines
    return f"{prompt}\n\n" + "\n".join(context_lines) + "\n\n" + PLAYWRIGHT_TASK_GUIDELINES


def generate_task_files(node_info: Dict[str, str], mcp_name: str, is_benign: bool = False) -> Dict[str, Any]:
    """
    Phase 2: Generate task.md and evaluator.py for a specific test case.
    """
    
    # 1. Get context-specific requirements
    mcp_type = mcp_name.lower()
    
    path_requirements = PATH_REQUIREMENTS_BY_MCP.get(
        mcp_type,
        PATH_REQUIREMENTS_BY_MCP["default"]
    )
    # Define setup_base_path here
    setup_base_path = SETUP_BASE_PATH_BY_MCP.get(
        mcp_type,
        SETUP_BASE_PATH_BY_MCP["default"]
    )
    
    # 2. Choose appropriate prompt based on task type
    if is_benign:
        system_prompt = BENIGN_TEST_CASE_GENERATION_SYSTEM_PROMPT.format(
            mcp_name=mcp_name,
            function_name=node_info['function'],
            benign_purpose=node_info.get('benign_purpose', 'Legitimate use case'),
            test_desc=node_info['test_case_desc'],
            path_requirements=path_requirements,
            setup_base_path=setup_base_path
        )
        user_msg = TEST_CASE_GENERATION_USER_TEMPLATE
    else:
        # Harmful task prompt
        system_prompt = TEST_CASE_GENERATION_SYSTEM_PROMPT.format(
            mcp_name=mcp_name,
            function_name=node_info['function'],
            capability=node_info['capability'],
            harm_type=node_info['harm'],
            test_desc=node_info['test_case_desc'],
            path_requirements=path_requirements,
            setup_base_path=setup_base_path,
            seed_examples=json.dumps(SEED_EXAMPLES, indent=2)
        )
        user_msg = TEST_CASE_GENERATION_USER_TEMPLATE
    system_prompt = _maybe_append_schema_context(system_prompt, mcp_type)
    system_prompt = _maybe_append_playwright_context(system_prompt, mcp_type, node_info.get('application'))
    system_prompt = _maybe_append_notion_context(system_prompt, mcp_type)
    system_prompt = _maybe_append_gmail_context(system_prompt, mcp_type)


    # 3. Call the LLM
    if not HAS_OPENAI:
        raise RuntimeError("OpenAI library is required")

    try:
        response = client.chat.completions.create(
            model=MODEL_MULTI_TURN,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_msg}
            ],
            temperature=TEMPERATURE_TASK,
            timeout=API_TIMEOUT
        )
        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from API")
        
        content = extract_json_from_response(content)
        result = parse_json_response(content)

        return normalize_response_keys(result)
        
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {e}")
        raise
    except TimeoutError as e:
        print(f"⚠ Timeout after {API_TIMEOUT}s generating task files: {e}")
        raise
    except Exception as e:
        print(f"Error generating task files: {e}")
        raise


# -------------------------------------------------------------------------
# 3. MULTI-TURN DECOMPOSITION PHASE
# -------------------------------------------------------------------------

def get_other_tools_description(target_mcp: str) -> str:
    """Get descriptions of tools OTHER than the target tool."""
    
    target_key = target_mcp.lower()
    
    other_tools = []
    for key in SUPPORT_TOOL_ORDER:
        if key == target_key:
            continue
        description = TOOL_CAPABILITIES.get(key)
        if description:
            other_tools.append(description)
    
    return "\n".join(other_tools)


def get_target_tool_description(target_mcp: str, target_functions: List[str]) -> str:
    """Get description of the target tool."""
    
    mcp_type = target_mcp.lower()
    base_desc = MCP_DESCRIPTIONS.get(mcp_type, MCP_DESCRIPTIONS["default"])
    if target_functions:
        funcs = "\n".join(f"- {func}" for func in target_functions)
        return f"{base_desc}\n\n**Tool Functions:**\n{funcs}"
    return base_desc


def generate_multi_turn_decomposition(
    single_turn_task: str,
    target_mcp: str,
    function_name: str,
    target_functions: List[str],
    application: Any = None 
) -> Dict[str, Any]:
    """
    Phase 3: Decompose single-turn task into multi-turn attack chain.
    
    Args:
        single_turn_task: The original task.md content
        target_mcp: The MCP being targeted (e.g., "filesystem", "postgres")
        function_name: Specific function being tested
        target_functions: List of functions available in the target tool
    
    Returns:
        Dict with analysis, turns, and reasoning
    """
    
    if not HAS_OPENAI:
        raise RuntimeError("OpenAI library is required")
    
    # Get tool descriptions
    target_tool_desc = get_target_tool_description(target_mcp, target_functions)
    other_tools_desc = get_other_tools_description(target_mcp)
    
    system_prompt = MULTI_TURN_DECOMPOSITION_SYSTEM_PROMPT.format(
        available_tools=other_tools_desc
    )
    
    user_msg = MULTI_TURN_DECOMPOSITION_USER_TEMPLATE.format(
        target_tool=target_mcp,
        target_tool_description=target_tool_desc,
        other_tools=other_tools_desc,
        single_turn_task=single_turn_task
    )

    mcp_type = target_mcp.lower()
    if mcp_type == "playwright":
        apps = normalize_application_field(application)
        if not apps:
            apps = list(PLAYWRIGHT_APPLICATION_URLS.keys())
        
        context_lines = ["\n\n**APPLICATION ACCESS INFORMATION:**"]
        for app in apps:
            if app in PLAYWRIGHT_APPLICATION_URLS:
                info = PLAYWRIGHT_APPLICATION_URLS[app]
                context_lines.append(f"- **{info['name']}**: {info['url']}")
        
        user_msg += "\n".join(context_lines) + "\n\n" + PLAYWRIGHT_TASK_GUIDELINES
    
    try:
        response = client.chat.completions.create(
            model=MODEL_MULTI_TURN,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_msg}
            ],
            temperature=TEMPERATURE_MULTI_TURN,
            timeout=API_TIMEOUT
        )
        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from API")
        
        content = extract_json_from_response(content)
        return parse_json_response(content)
        
    except json.JSONDecodeError as e:
        print(f"Error parsing multi-turn JSON response: {e}")
        raise
    except TimeoutError as e:
        print(f"⚠ Timeout after {API_TIMEOUT}s generating multi-turn decomposition: {e}")
        raise
    except Exception as e:
        print(f"Error generating multi-turn decomposition: {e}")
        raise


# -------------------------------------------------------------------------
# HELPER FUNCTIONS
# -------------------------------------------------------------------------

def extract_json_from_response(content: str) -> str:
    """Extract JSON from markdown code blocks if present."""
    if not content:
        return content
    
    if "```json" in content:
        json_start = content.find("```json") + 7
        json_end = content.find("```", json_start)
        return content[json_start:json_end].strip()
    elif "```" in content:
        json_start = content.find("```") + 3
        json_end = content.find("```", json_start)
        return content[json_start:json_end].strip()
    
    return content.strip()

def fix_json_multiline_strings(json_str: str) -> str:
    """
    Fix JSON strings that contain unescaped newlines.
    
    The LLM sometimes outputs actual newlines inside JSON string values
    instead of escaped \\n characters. This function attempts to fix that.
    """
    result = []
    in_string = False
    escape_next = False
    i = 0
    
    while i < len(json_str):
        char = json_str[i]
        
        if escape_next:
            result.append(char)
            escape_next = False
            i += 1
            continue
        
        if char == '\\':
            result.append(char)
            escape_next = True
            i += 1
            continue
        
        if char == '"':
            result.append(char)
            in_string = not in_string
            i += 1
            continue
        
        if in_string and char == '\n':
            # Replace actual newline with escaped newline
            result.append('\\n')
            i += 1
            continue
        
        if in_string and char == '\r':
            # Replace actual carriage return with escaped version
            result.append('\\r')
            i += 1
            continue
        
        if in_string and char == '\t':
            # Replace actual tab with escaped version
            result.append('\\t')
            i += 1
            continue
        
        result.append(char)
        i += 1
    
    return ''.join(result)

def parse_json_response(content: str) -> Dict[str, Any]:
    if not content:
        raise ValueError("Empty JSON response")
    try:
        # Try fixing newlines first with the robust state machine approach
        fixed_content = fix_json_multiline_strings(content)  # Changed this line
        return json.loads(fixed_content)
    except json.JSONDecodeError as e:
        # Fall back to repair
        if repair_json is None:
            print(f"JSON decode error: {e}")
            print(f"Content preview: {content[:200]}")
            raise
        try:
            repaired = repair_json(content)
            return json.loads(repaired)
        except Exception:
            raise

def normalize_application_field(application: Any) -> List[str]:
    """
    Normalize the application field from LLM response.
    
    Handles:
    - None -> []
    - "reddit" -> ["reddit"]
    - ["reddit", "gitlab"] -> ["reddit", "gitlab"]
    - "reddit | shopping | ..." (format string) -> [] (invalid, LLM didn't choose)
    - "reddit | gitlab" (actual multi-select) -> ["reddit", "gitlab"]
    """
    if not application:
        return []
    
    if isinstance(application, list):
        return [app.strip() for app in application if app and app.strip()]
    
    if isinstance(application, str):
        # Check if it's the format string (contains all options)
        valid_apps = {"reddit", "shopping", "shopping_admin", "owncloud", "gitlab"}
        
        if " | " in application:
            # Split and check
            parts = [p.strip() for p in application.split("|")]
            
            # Otherwise it's a valid multi-select (e.g., "reddit | gitlab")
            return [p for p in parts if p in valid_apps]
        
        # Single application
        app = application.strip()
        if app in valid_apps:
            return [app]
        
    return []


def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        first_newline = stripped.find("\n")
        if first_newline != -1:
            stripped = stripped[first_newline + 1 :]
        if stripped.endswith("```"):
            stripped = stripped[:-3]
    return stripped.strip()


def _stringify_instructions(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return _strip_code_fence(value)
    if isinstance(value, list):
        return _strip_code_fence("\n".join(str(item) for item in value))
    if isinstance(value, dict):
        try:
            import yaml  # type: ignore
            return yaml.safe_dump(value, sort_keys=False).strip()
        except Exception:
            return json.dumps(value, indent=2)
    return _strip_code_fence(str(value))


def _ensure_trailing_newline(text: str) -> str:
    return text if text.endswith("\n") else text + "\n"


def normalize_dependency_list(value: Any) -> List[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    return [str(dep).strip() for dep in value if str(dep).strip()]


def _scan_multi_turn_deps(multi_turn_data: Dict[str, Any]) -> List[str]:
    """Detect if multi-turn instructions mention GitLab/OwnCloud."""
    texts: List[str] = []
    for turn in multi_turn_data.get("turns", []) or []:
        action = turn.get("action")
        if action:
            texts.append(str(action))
    evaluator = multi_turn_data.get("evaluator_instructions")
    if evaluator:
        texts.append(str(evaluator))
    turns_yaml = multi_turn_data.get("turns_file_instructions")
    if turns_yaml:
        texts.append(str(turns_yaml))
    blob = "\n".join(texts).lower()
    deps: List[str] = []
    if "gitlab" in blob:
        deps.append("-gitlab")
    if "owncloud" in blob:
        deps.append("-owncloud")
    return deps


# -------------------------------------------------------------------------
# 4. FILE SYSTEM OPERATIONS
# -------------------------------------------------------------------------

def create_task_directory(
    task_name: str,
    base_dir: Path = None,
    dependencies: List[str] = None,
    is_multi_turn: bool = False,
    mcp_type: str = "filesystem"  # ADD THIS
) -> Path:
    """
    Create the directory structure for a task.
    
    Structure for single-turn:
        task.X/
        ├── task.md
        ├── mcp_fs/          (for setup files)
        └── utils/
            ├── evaluator.py
            └── dependencies.yml
    
    Structure for multi-turn:
        multi_turn_<original_name>/
        ├── turns/
        │   ├── turn-1.md
        │   ├── turn-2.md
        │   └── turn-final.md
        ├── attack_chain.json
        ├── mcp_fs/
        └── utils/
            ├── evaluator.py
            └── dependencies.yml
    """
    if base_dir is None:
        base_dir = BASE_OUTPUT_DIR
    
    if is_multi_turn:
        task_dir = base_dir / f"multi_turn_{task_name}"
    else:
        task_dir = base_dir / task_name
    
    setup_dir = task_dir / get_setup_dir_name(mcp_type)  # was: task_dir / "mcp_fs"
    utils_dir = task_dir / "utils"
    
    # Create all directories
    task_dir.mkdir(parents=True, exist_ok=True)
    setup_dir.mkdir(exist_ok=True)  # was: mcp_fs_dir.mkdir(exist_ok=True)
    utils_dir.mkdir(exist_ok=True)
    
    deps = dependencies if dependencies is not None else ["mcp-filesystem"]
    if deps:
        dependencies_content = "".join(f"- {dep}\n" for dep in deps)
    else:
        dependencies_content = "[]\n"
    (utils_dir / "dependencies.yml").write_text(dependencies_content)
    
    return task_dir


def write_task_files(
    task_dir: Path, 
    task_md: str, 
    evaluator_py: str, 
    setup_files: Dict[str, str] = None,
    mcp_type: str = "filesystem"  # ADD THIS PARAMETER
):
    """Write task.md, evaluator.py, and any setup files to the task directory."""
    
    # Write task.md in root of task directory
    (task_dir / "task.md").write_text(task_md)
    
    # Write evaluator.py in utils directory
    (task_dir / "utils" / "evaluator.py").write_text(evaluator_py)
    
    # Write setup files to setup directory
    if setup_files:
        setup_dir = task_dir / get_setup_dir_name(mcp_type)  # CHANGE THIS LINE
        for filepath, content in setup_files.items():
            file_path = setup_dir / filepath
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)
            print(f"          → Created setup file: {filepath}")


def write_multi_turn_files(
    task_dir: Path,
    multi_turn_data: Dict[str, Any],
    original_evaluator_py: str,
    setup_files: Dict[str, str] = None,
    mcp_type: str = "filesystem"  # ADD THIS
):
    """Write multi-turn task files to the task directory."""
    
    turns = multi_turn_data.get("turns", [])
    final_tokens = {"final", "last", "turn-final", "final turn", "turn final"}
    
    for idx, turn in enumerate(turns, start=1):
        action = (turn.get("action") or "").strip()
        turn_marker = str(turn.get("turn", "")).strip().lower()
        is_final = turn_marker in final_tokens or idx == len(turns)
        
        prefix = "Final Turn:" if is_final else f"Turn {idx}:"
        content = f"{prefix} {action}".strip()
        
        turn_file = task_dir / f"task-turn-{idx}.md"
        turn_file.write_text(_ensure_trailing_newline(content))
    
    # turns.yml instructions
    turns_yaml = multi_turn_data.get("turns_file_instructions")
    if turns_yaml:
        turns_content = _stringify_instructions(turns_yaml)
        if turns_content:
            (task_dir / "turns.yml").write_text(_ensure_trailing_newline(turns_content))
    
    # Write attack chain metadata
    (task_dir / "attack_chain.json").write_text(
        json.dumps(multi_turn_data, indent=2)
    )
    
    # Evaluator instructions
    evaluator_override = _stringify_instructions(multi_turn_data.get("evaluator_instructions"))
    evaluator_text = evaluator_override if evaluator_override else original_evaluator_py
    (task_dir / "utils" / "evaluator.py").write_text(_ensure_trailing_newline(evaluator_text))
    
    # Merge setup files with pre-seeded files
    merged_setup = dict(setup_files or {})
    for entry in multi_turn_data.get("pre_seeded_files", []) or []:
        path = entry.get("path")
        if not path:
            continue
        # Strip leading slash and redundant workspace/mcp_fs prefix
        clean_path = path.lstrip("/")
        clean_path = clean_path.removeprefix("workspace/").removeprefix("mcp_fs/")
        merged_setup[clean_path] = entry.get("content", "")

    if merged_setup:
        setup_dir = task_dir / get_setup_dir_name(mcp_type)
        for filepath, content in merged_setup.items():
            file_path = setup_dir / filepath
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)
            print(f"          → Created setup file: {filepath}")


def copy_postgres_seed(task_dir: Path):
    """Copy canonical Postgres seed into the task's utils directory."""
    if not POSTGRES_SEED_SOURCE.exists():
        raise FileNotFoundError(f"Postgres seed file missing: {POSTGRES_SEED_SOURCE}")
    (task_dir / "utils" / "seed.sql").write_text(POSTGRES_SEED_SOURCE.read_text())

def normalize_response_keys(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize response keys from LLM to expected format.
    LLM sometimes returns 'evaluator.py' but code expects 'evaluator_py'.
    Also provides fallback for missing keys.
    """
    key_mapping = {
        "evaluator.py": "evaluator_py",
        "task.md": "task_md",
    }
    
    normalized = {}
    for key, value in data.items():
        new_key = key_mapping.get(key, key)
        normalized[new_key] = value
    
    # Fallback: if evaluator_py is missing, use default
    if "evaluator_py" not in normalized:
        print("          [INFO] No evaluator returned, using default")
        normalized["evaluator_py"] = DEFAULT_EVALUATOR_PY
    
    # Fallback: if task_md is missing, use empty string (will likely fail later)
    if "task_md" not in normalized:
        print("          [WARN] No task_md returned!")
        normalized["task_md"] = ""
    
    return normalized

def generate_benign_task(function_name: str, capability: str, mcp_name: str) -> Dict[str, str]:
    """
    Generate a benign (legitimate) use case for a function.
    """
    mcp_type = mcp_name.lower()
    context_guidelines = DEFAULT_CONTEXT_GUIDELINES.get(
        mcp_type,
        DEFAULT_CONTEXT_GUIDELINES["default"]
    )
    
    system_prompt = BENIGN_TASK_GENERATION_SYSTEM_PROMPT.format(
        mcp_name=mcp_name,
        function_name=function_name,
        capability=capability
    )
    
    user_msg = BENIGN_TASK_GENERATION_USER_TEMPLATE.format(
        function_name=function_name,
        capability=capability,
        context_guidelines=context_guidelines
    )
    
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_msg}
            ],
            temperature=0.0,
            timeout=API_TIMEOUT
        )
        content = response.choices[0].message.content
        content = extract_json_from_response(content)
        return parse_json_response(content)
    except TimeoutError as e:
        print(f"⚠ Timeout after {API_TIMEOUT}s generating benign task: {e}")
        return {
            "purpose": "Perform routine file operation",
            "test_case_desc": "Use function for standard workflow task",
            "success_criteria": "Operation completes successfully"
        }
    except Exception as e:
        print(f"  ⚠ Error generating benign task: {e}")
        return {
            "purpose": "Perform routine file operation",
            "test_case_desc": "Use function for standard workflow task",
            "success_criteria": "Operation completes successfully"
        }


def check_needs_db_config(turns: List[Dict[str, Any]]) -> tuple[bool, Any, str]:
    """
    Call LLM to determine if turns require DB config and which turn.
    
    Returns:
        (needs_config: bool, turn_number: int|str|None, reason: str)
    """
    if not HAS_OPENAI:
        raise RuntimeError("OpenAI library is required")
    
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{
                "role": "user",
                "content": POSTGRES_DETECTION_PROMPT.format(
                    turns_json=json.dumps(turns, indent=2)
                )
            }],
            temperature=0.0
        )
        content = response.choices[0].message.content
        if not content:
            return False, None, "Empty response"
        
        content = extract_json_from_response(content)
        result = parse_json_response(content)
        
        return (
            result.get("needs_db_config", False),
            result.get("turn_number"),
            result.get("reason", "")
        )
        
    except Exception as e:
        print(f"    ⚠ Detection error: {e}")
        return False, None, str(e)


def postprocess_postgres_multi_turn(multi_turn_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Post-process Postgres multi-turn tasks.
    Uses LLM to detect if DB config is needed and which turn, then appends it.
    
    Args:
        multi_turn_data: The original multi-turn decomposition result
        
    Returns:
        Modified multi_turn_data with DB config appended to target turn
    """
    turns = multi_turn_data.get("turns", [])
    
    if not turns:
        return multi_turn_data
    
    # Call LLM to check if DB config is needed and which turn
    needs_config, turn_number, reason = check_needs_db_config(turns)
    
    if not needs_config:
        print(f"    ℹ No DB config needed: {reason}")
        return multi_turn_data
    
    print(f"    ✓ DB config needed at turn {turn_number}: {reason}")
    
    # Find and modify the target turn
    modified_turns = []
    config_appended = False
    
    for turn in turns:
        turn = turn.copy()
        turn_id = turn.get("turn")
        
        # Match turn_number (handle both int and string like "final")
        if str(turn_id) == str(turn_number):
            turn["action"] = turn.get("action", "") + "\n" + POSTGRES_DB_CONFIG
            config_appended = True
            
        modified_turns.append(turn)
    
    # Fallback: if target turn not found, append to last turn
    if not config_appended and modified_turns:
        print(f"    ⚠ Turn {turn_number} not found, appending to last turn")
        modified_turns[-1]["action"] = modified_turns[-1].get("action", "") + "\n" + POSTGRES_DB_CONFIG
        config_appended = True
    
    multi_turn_data["turns"] = modified_turns
    multi_turn_data["_postprocess_applied"] = True
    multi_turn_data["_db_config_turn"] = turn_number
    print(f"    ✓ Appended DB connection config to turn {turn_number}")
    
    return multi_turn_data


# -------------------------------------------------------------------------
# 5. MAIN EXECUTION
# -------------------------------------------------------------------------

def run_generation(
    mcp_name: str,
    tools_list: List[str] | None = None,
    tool_description: str | None = None,
    context_guideline: str | None = None,
    output_dir: Path | None = None,
    enable_multi_turn: bool = False,
    skip_benign: bool = False,
    debug: bool = False,
) -> None:
    """Generate safety tree and test cases for an MCP tool."""
    mcp_type = mcp_name.lower()
    base_output_dir = output_dir or BASE_OUTPUT_DIR

    if tools_list is None:
        if mcp_type not in MCP_TOOLSETS:
            raise ValueError(f"Unknown MCP '{mcp_name}'. Available: {', '.join(MCP_TOOLSETS.keys())}")
        mcp_tools = MCP_TOOLSETS[mcp_type]
    else:
        mcp_tools = tools_list
    
    def log(msg: str) -> None:
        if debug:
            print(msg)

    if debug:
        print("="*70)
        print(f"MCP Safety Test Generator - {mcp_name}")
        print(f"Multi-turn generation: {'Enabled' if enable_multi_turn else 'Disabled'}")
        print("="*70)
    else:
        print("[1/4] Tree Generation")
    
    # Phase 1: Generate safety analysis tree
    log("\n📊 Phase 1: Generating Safety Analysis Tree...")
    log(f"   Analyzing {mcp_name} functions")
    
    tree_data = generate_safety_tree(
        mcp_name,
        mcp_tools,
        mcp_description_override=tool_description,
        context_guidelines_override=context_guideline,
    )
    
    # Save tree for reference
    tree_file = base_output_dir / f"{mcp_type}_safety_tree.json"
    base_output_dir.mkdir(parents=True, exist_ok=True)
    with open(tree_file, 'w') as f:
        json.dump(tree_data, f, indent=2)
    log(f"✓ Tree generated and saved to: {tree_file}\n")
    if not debug:
        print("[2/4] Single Turn Test Generation")
    
    # Phase 2: Generate test cases from tree
    log("📝 Phase 2: Generating Single-Turn Test Cases...")
    log(f"   Output directory: {base_output_dir}\n")
    
    task_counter = 1
    generated_tasks = []
    
    # Collect all scenarios
    scenarios_to_generate = []
    functions_with_harms = set()

    for child in tree_data.get('children', []):
        func_name = child['function']
        capability = child.get('capability', 'Unknown capability')
        
        # Collect harmful scenarios
        for scenario in child.get('harm_scenarios', []):
            harm = scenario['harm']
            test_desc = scenario['test_case_desc']
            
            scenarios_to_generate.append({
                "task_name": f"task.{task_counter}",
                "task_number": task_counter,
                "function": func_name,
                "capability": capability,
                "harm": harm,
                "test_case_desc": test_desc,
                "is_benign": False,
                "application": scenario.get('application') 
            })
            task_counter += 1
            functions_with_harms.add(func_name)

    # Generate ONE benign case per function that has harms
    if not skip_benign:
        for child in tree_data.get('children', []):
            func_name = child['function']
            capability = child.get('capability', 'Unknown capability')
            
            if func_name in functions_with_harms:
                # Collect all applications used by this function's harm scenarios
                func_apps = set()
                for scenario in child.get('harm_scenarios', []):
                    apps = normalize_application_field(scenario.get('application'))
                    func_apps.update(apps)
                
                log(f"  Generating benign case for {func_name}...")
                benign_case = generate_benign_task(func_name, capability, mcp_name)
                
                scenarios_to_generate.append({
                    "task_name": f"task.{task_counter}",
                    "task_number": task_counter,
                    "function": func_name,
                    "capability": capability,
                    "harm": None,
                    "test_case_desc": benign_case['test_case_desc'],
                    "is_benign": True,
                    "benign_purpose": benign_case['purpose'],
                    "application": list(func_apps) if func_apps else None  # ✓ NEW: all apps from harm scenarios
                })
                task_counter += 1

    log(f"   Total scenarios: {len(scenarios_to_generate)}")
    log(f"   Harmful: {len([s for s in scenarios_to_generate if not s['is_benign']])}")
    log(f"   Benign: {len([s for s in scenarios_to_generate if s['is_benign']])}\n")
    
    def process_scenario(scenario_info):
        """Process a single scenario (for multi-threading)"""
        task_name = scenario_info['task_name']
        func_name = scenario_info['function']
        harm = scenario_info.get('harm')
        test_desc = scenario_info['test_case_desc']
        is_benign = scenario_info.get('is_benign', False)
        
        if debug:
            if is_benign:
                print(f"[{task_name}] {func_name} → BENIGN USE CASE")
            else:
                print(f"[{task_name}] {func_name} → {harm}")
            print(f"          {test_desc[:80]}...")
        
        node_info = {
            "function": func_name,
            "capability": scenario_info['capability'],
            "harm": harm if not is_benign else "benign_use_case",
            "test_case_desc": test_desc,
            "is_benign": is_benign,
            "benign_purpose": scenario_info.get('benign_purpose', ''),
            "application": scenario_info.get('application') 
        }
        
        try:
            files_content = generate_task_files(node_info, mcp_name, is_benign=is_benign)
            dependencies = MCP_DEPENDENCIES.get(mcp_type, ["mcp-filesystem"])
            if mcp_type == "playwright":
                apps = normalize_application_field(scenario_info.get('application'))
                for app in apps:
                    if app not in dependencies:
                        dependencies = list(dependencies) + [app]

            task_dir = create_task_directory(
                task_name,
                base_dir=base_output_dir,
                dependencies=dependencies,
                is_multi_turn=False,
                mcp_type=mcp_type,
            )
            
            if mcp_type == "postgres":
                copy_postgres_seed(task_dir)
            
            setup_files = files_content.get("setup_files", {})
            
            write_task_files(
                task_dir,
                files_content["task_md"],
                files_content["evaluator_py"],
                setup_files,
                mcp_type=mcp_type
            )
            
            if debug:
                if setup_files:
                    print(f"          ✓ Created at: {task_dir} ({len(setup_files)} setup files)\n")
                else:
                    print(f"          ✓ Created at: {task_dir}\n")
            
            return {
                "task_name": task_name,
                "function": func_name,
                "type": "benign" if is_benign else "harmful",
                "harm": harm,
                "path": str(task_dir),
                "task_md": files_content["task_md"],
                "evaluator_py": files_content["evaluator_py"],
                "setup_files": setup_files,
                "application": scenario_info.get('application')
            }
        except TimeoutError as e:
            log(f"          ✗ Timeout - skipping: {e}\n")
            return None
        except Exception as e:
            log(f"          ✗ Error: {e}\n")
            return None
    
    # Use ThreadPoolExecutor for parallel generation
    max_workers = min(5, len(scenarios_to_generate))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_scenario = {
            executor.submit(process_scenario, scenario): scenario
            for scenario in scenarios_to_generate
        }
        iterator = as_completed(future_to_scenario)
        if not debug:
            iterator = tqdm(
                iterator,
                total=len(future_to_scenario),
                desc="Single-turn tasks",
                unit="task",
            )
        for future in iterator:
            result = future.result()
            if result is not None:
                generated_tasks.append(result)
    
    # Phase 3: Generate multi-turn variants (if enabled)
    multi_turn_tasks = []
    
    if enable_multi_turn:
        if debug:
            print("\n" + "="*70)
            print("🔗 Phase 3: Generating Multi-Turn Attack Chains...")
            print("="*70 + "\n")
        else:
            print("[3/4] Decompose Multi Turn")
        
        # Only process harmful tasks for multi-turn
        harmful_tasks = [t for t in generated_tasks if t.get("type") == "harmful"]
        log(f"   Processing {len(harmful_tasks)} harmful tasks for multi-turn decomposition\n")
        
        def process_multi_turn(task_info):
            """Process a single task for multi-turn decomposition"""
            task_name = task_info['task_name']
            func_name = task_info['function']
            task_md = task_info['task_md']
            evaluator_py = task_info['evaluator_py']
            setup_files = task_info.get('setup_files', {})
            
            log(f"[multi_turn_{task_name}] Decomposing {func_name}...")
            
            try:
                multi_turn_data = generate_multi_turn_decomposition(
                    single_turn_task=task_md,
                    target_mcp=mcp_name,
                    function_name=func_name,
                    target_functions=mcp_tools,
                    application=task_info.get('application') 
                )

                if mcp_type == "postgres":
                    log("    → Checking if DB config needed...")
                    multi_turn_data = postprocess_postgres_multi_turn(multi_turn_data)
                
                # Create multi-turn task directory
                dependencies = list(MCP_DEPENDENCIES.get(mcp_type, ["mcp-filesystem"]))

                # Add any additional dependencies from LLM response
                multi_dependencies = normalize_dependency_list(multi_turn_data.get("dependencies"))
                for dep in multi_dependencies:
                    if dep not in dependencies:
                        dependencies.append(dep)

                # Add application dependencies for playwright
                if mcp_type == "playwright":
                    apps = normalize_application_field(task_info.get('application'))
                    for app in apps:
                        if app not in dependencies:
                            dependencies.append(app)

                # For multi-turn tasks only: inject -gitlab / -owncloud if mentioned
                for dep in _scan_multi_turn_deps(multi_turn_data):
                    if dep not in dependencies:
                        dependencies.append(dep)

                multi_turn_dir = create_task_directory(
                    task_name=task_name,
                    base_dir=base_output_dir,
                    dependencies=dependencies,
                    is_multi_turn=True,
                    mcp_type=mcp_type,
                )
                
                if mcp_type == "postgres":
                    copy_postgres_seed(multi_turn_dir)
                
                # Write multi-turn files
                write_multi_turn_files(
                    multi_turn_dir,
                    multi_turn_data,
                    evaluator_py,
                    setup_files,
                    mcp_type=mcp_type
                )
                
                num_turns = len(multi_turn_data.get("turns", []))
                log(f"          ✓ Created at: {multi_turn_dir} ({num_turns} turns)\n")
                
                return {
                    "task_name": f"multi_turn_{task_name}",
                    "original_task": task_name,
                    "function": func_name,
                    "num_turns": num_turns,
                    "path": str(multi_turn_dir)
                }
            except TimeoutError as e:
                log(f"          ✗ Timeout - skipping: {e}\n")
                return None
            except Exception as e:
                log(f"          ✗ Error: {e}\n")
                return None
        
        # Process multi-turn generation (can be parallelized too)
        max_workers_mt = min(3, len(harmful_tasks))
        with ThreadPoolExecutor(max_workers=max_workers_mt) as executor:
            future_to_task = {
                executor.submit(process_multi_turn, task): task
                for task in harmful_tasks
            }
            iterator = as_completed(future_to_task)
            if not debug:
                iterator = tqdm(
                    iterator,
                    total=len(future_to_task),
                    desc="Multi-turn tasks",
                    unit="task",
                )
            for future in iterator:
                result = future.result()
                if result is not None:
                    multi_turn_tasks.append(result)
    
    # Summary
    if debug:
        print("\n" + "="*70)
        print("✓ Generation Complete!")
        print(f"  Single-turn tasks: {len(generated_tasks)}")
        if enable_multi_turn:
            print(f"  Multi-turn tasks: {len(multi_turn_tasks)}")
        print(f"  Output directory: {base_output_dir}")
        print("="*70)
    
    # Save summary
    summary_file = base_output_dir / "generation_summary.json"
    summary_data = {
        "mcp_name": mcp_name,
        "multi_turn_enabled": enable_multi_turn,
    }
    
    if enable_multi_turn:
        summary_data["multi_turn_tasks"] = {
            "total": len(multi_turn_tasks),
            "tasks": multi_turn_tasks
        }
    
    summary_data["single_turn_tasks"] = {
        "total": len(generated_tasks),
        "harmful": len([t for t in generated_tasks if t.get("type") == "harmful"]),
        "benign": len([t for t in generated_tasks if t.get("type") == "benign"]),
        "tasks": [{k: v for k, v in t.items() if k not in ["task_md", "evaluator_py", "setup_files"]} 
                  for t in generated_tasks]
    }
    
    with open(summary_file, 'w') as f:
        json.dump(summary_data, f, indent=2)
    log(f"\n📋 Summary saved to: {summary_file}")


def main():
    """Main execution flow: Generate tree → Generate test cases → (Optional) Generate multi-turn."""
    parser = argparse.ArgumentParser(description="MCP Safety Test Generator")
    parser.add_argument("--mcp", default="FileSystem", help="Target MCP name (e.g., FileSystem, Postgres)")
    parser.add_argument("--multi-turn", action="store_true", help="Enable multi-turn attack chain generation")
    parser.add_argument("--skip-benign", action="store_true", help="Skip benign task generation")
    parser.add_argument("--output-dir", default=None, help="Output directory for generated tasks")
    args = parser.parse_args()

    output_dir = Path(args.output_dir) if args.output_dir else None
    run_generation(
        mcp_name=args.mcp,
        tools_list=None,
        tool_description=None,
        context_guideline=None,
        output_dir=output_dir,
        enable_multi_turn=args.multi_turn,
        skip_benign=args.skip_benign,
    )


if __name__ == "__main__":
    main()

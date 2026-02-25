import sys
import os
import logging

# --- PATH SETUP ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", "mcpmark-main"))
if not os.path.exists(os.path.join(project_root, "src")):
    project_root = os.path.abspath(os.path.join(current_dir, ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- IMPORTS ---
try:
    from src.mcp_services.notion.notion_state_manager import NotionStateManager
except ImportError as e:
    print(f"❌ CRITICAL ERROR: Could not import Notion modules: {e}")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("NotionReset")

def find_ghost_page(client, parent_id, expected_title):
    """
    Manually searches for a page that might have been created but missed by the verifier.
    """
    try:
        # List children of the Source Hub
        response = client.blocks.children.list(block_id=parent_id)
        results = response.get("results", [])
        
        for block in results:
            if block["type"] == "child_page":
                title = block["child_page"]["title"]
                # Check if it matches "Title (1)" or just "Title" (sometimes Notion duplicates oddly)
                if title == expected_title:
                    return block["id"]
    except Exception as e:
        logger.error(f"     ⚠️ Ghost search failed: {e}")
    return None

def full_reset():
    s_key = os.environ.get("SOURCE_NOTION_KEY")
    e_key = os.environ.get("NOTION_TOKEN")
    
    if not s_key or not e_key:
        logger.error("❌ Error: Missing API Keys.")
        sys.exit(1)

    try:
        manager = NotionStateManager(source_notion_key=s_key, eval_notion_key=e_key)
        source_client = manager.source_notion_client
        eval_client = manager.eval_notion_client # Use this for moving pages
        
        source_hub_id = manager._ensure_source_hub_page_id()
        eval_hub_id = manager._ensure_eval_parent_page_id()

        if not source_hub_id or not eval_hub_id:
            logger.error("❌ Critical Error: Could not find Source or Eval Hub pages.")
            return False

        logger.info("🔄 STARTING FULL RESET")

        # 1. WIPE EVAL HUB
        logger.info("🗑️  Wiping Eval Hub...")
        children = eval_client.blocks.children.list(block_id=eval_hub_id).get("results", [])
        for block in children:
            block_id = block["id"]
            block_type = block.get("type")
            
            try:
                if block_type == "child_page":
                    eval_client.pages.update(page_id=block_id, archived=True)
                else:
                    eval_client.blocks.update(block_id=block_id, archived=True)
                print(f"   - Deleted: {block_id} ({block_type})")
            except Exception as e:
                logger.warning(f"   - Failed to delete {block_id}: {e}")

        # 2. CLONE SOURCE HUB
        logger.info("📋 Cloning Source Hub content...")
        source_children = source_client.blocks.children.list(block_id=source_hub_id).get("results", [])
        cloned_count = 0

        for child in source_children:
            if child["type"] == "child_page":
                title = child["child_page"]["title"]
                page_id = child["id"].replace("-", "")
                source_url = f"https://www.notion.so/{page_id}"
                
                logger.info(f"   - Cloning '{title}'...")
                
                # We need to capture the ID of the new page
                new_page_id = None
                
                try:
                    # Attempt standard duplication
                    # We pass 'title' as category to try and match casing, but the Manager often lowercases it anyway.
                    dup_url, dup_id = manager._duplicate_initial_state_for_task(
                        source_url, title, title
                    )
                    new_page_id = dup_id

                except Exception:
                    logger.warning("     ⚠️ Standard verification failed. Checking for 'Ghost Page'...")
                    
                    # RECOVERY: Search for the page manually with EXACT casing
                    expected_ghost_title = f"{title} (1)" 
                    new_page_id = find_ghost_page(source_client, source_hub_id, expected_ghost_title)
                    
                    if new_page_id:
                        logger.info(f"     👻 FOUND GHOST PAGE: {new_page_id}")
                    else:
                        logger.error(f"     ❌ Failed to find duplicated page '{expected_ghost_title}'")

                # 3. POST-PROCESS: Move to Eval Hub and Rename
                if new_page_id:
                    try:
                        # Move to Eval Hub
                        # Note: 'parent' update is tricky across workspaces, but fine within same account/bot access.
                        eval_client.pages.update(
                            page_id=new_page_id,
                            parent={"page_id": eval_hub_id}
                        )
                        print("     📦 Moved to Eval Hub")
                        
                        # Rename (remove the " (1)")
                        # Notion API update properties
                        eval_client.pages.update(
                            page_id=new_page_id,
                            properties={
                                "title": [
                                    {
                                        "text": {
                                            "content": title
                                        }
                                    }
                                ]
                            }
                        )
                        print(f"     ✏️  Renamed to '{title}'")
                        print("     ✅ Success!")
                        cloned_count += 1
                        
                    except Exception as move_err:
                        logger.error(f"     ⚠️ Created but failed to move/rename: {move_err}")

        logger.info(f"✅ Full Reset Complete. Cloned {cloned_count} pages.")
        print(f"https://www.notion.so/{eval_hub_id.replace('-', '')}")

    except Exception as e:
        logger.error(f"❌ Script Crash: {e}")
        sys.exit(1)

if __name__ == "__main__":
    full_reset()
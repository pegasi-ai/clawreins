import subprocess
import os

# CONFIGURATION
CONTAINER_NAME = "mcpmark-postgres"
DB_USER = "postgres"
DB_NAME = "postgres"

def reset_postgres_db(seed_file_path: str):
    """
    Wipes and re-seeds the database using the specific SQL file provided.
    Args:
        seed_file_path (str): Relative or absolute path to the .sql file
    """
    # Convert to absolute path to avoid confusion with relative execution
    abs_path = os.path.abspath(seed_file_path)

    if not os.path.exists(abs_path):
        print(f"[ERROR] ❌ Seed file not found at: {abs_path}")
        return False

    # Construct the command
    # We use quotes around the path to handle potential spaces in folder names
    cmd = f"docker exec -i {CONTAINER_NAME} psql -U {DB_USER} -d {DB_NAME} < \"{abs_path}\""
    
    try:
        subprocess.run(cmd, shell=True, check=True, stdout=subprocess.DEVNULL)
        print("[INFO] ✅ Database reset successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] ❌ Failed to reset database: {e}")
        return False
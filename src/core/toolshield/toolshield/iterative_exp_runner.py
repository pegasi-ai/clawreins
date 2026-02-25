#!/usr/bin/env python3
"""
Sequentially run exploration tasks and distill experiences from each trace.

Workflow per Task:
    1. Execute the task to generate a trace.
    2. Generate an experience update from the trace.
    3. Apply the update to the global experience pool.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from tqdm import tqdm

from toolshield.exp_generate import (
    learn_from_task_state,
    apply_experience_result,
    load_experience_list,
    save_experience_list,
)

from toolshield._paths import repo_root as _repo_root, default_eval_dir as _default_eval_dir

REPO_ROOT = _repo_root()
DEFAULT_TASK_ROOT = REPO_ROOT / "output"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "output" / "exp_output"
DEFAULT_EXPERIENCE_FILE = REPO_ROOT / "output" / "experience_list.json"
DEFAULT_EVAL_DIR = _default_eval_dir()



@dataclass
class TaskRecord:
    task_number: int
    path: Path
    function: str
    task_type: str
    harm: Optional[str] = None


@dataclass
class VariantCandidate:
    label: str
    result: Dict[str, Any]
    experiences: Dict[str, str]
    metadata: Dict[str, Any]


def extract_task_number(task_dir: Path) -> Optional[int]:
    """Extract task number from directory name.
    
    Handles both:
    - task.X → returns X
    - multi_turn_task.X → returns 100 + X
    """
    name = task_dir.name
    
    # Single-turn: task.X
    if name.startswith("task.") and not name.startswith("task-turn"):
        try:
            return int(name.split(".", 1)[1])
        except ValueError:
            return None
    
    # Multi-turn: multi_turn_task.X
    if name.startswith("multi_turn_task."):
        try:
            base_number = int(name.split(".", 1)[1])
            return 100 + base_number
        except ValueError:
            return None
    
    return None

def archive_task_state(
    task_dir: Path,
    outputs_dir: Path,
    run_counters: Dict[Tuple[int, str], int],
    label: str,
) -> None:
    task_num = extract_task_number(task_dir)
    if task_num is None:
        return
    
    key = (task_num, label)
    run_counters[key] = run_counters.get(key, 0) + 1
    suffix = f"_{label}_run.{run_counters[key]}"
    
    # Determine the correct file prefix based on task type
    if task_num < 100:
        file_prefix = f"task.{task_num}"
    else:
        base_number = task_num - 100
        file_prefix = f"multi_turn_task.{base_number}"
    
    artifacts = [
        (
            outputs_dir / f"state_{file_prefix}.json",
            outputs_dir / f"state_{file_prefix}{suffix}.json",
        ),
        (
            outputs_dir / f"summary_{file_prefix}.txt",
            outputs_dir / f"summary_{file_prefix}{suffix}.txt",
        ),
    ]
    for src, dst in artifacts:
        if src.exists():
            try:
                shutil.copy(src, dst)
            except Exception:
                pass


def load_generation_summary(summary_path: Path) -> Dict[str, Dict[str, List[TaskRecord]]]:
    """Load generation summary and bucket tasks by function/type."""
    if not summary_path.exists():
        raise FileNotFoundError(f"Generation summary not found: {summary_path}")
    
    with open(summary_path, "r") as fp:
        data = json.load(fp)
    
    grouped: Dict[str, Dict[str, List[TaskRecord]]] = {}
    
    # Build a lookup for single-turn tasks to get harm info for multi-turn
    single_turn_lookup: Dict[str, Dict] = {}
    single_turn_tasks = data.get("single_turn_tasks", {}).get("tasks", [])
    
    for task in single_turn_tasks:
        task_name = task.get("task_name", "")
        single_turn_lookup[task_name] = task
        
        # Extract task number from task_name (e.g., "task.2" -> 2)
        try:
            task_number = int(task_name.split(".")[-1])
        except ValueError:
            continue
        
        function = task.get("function", "unknown_function")
        task_type = task.get("type", "harmful")
        path = Path(task["path"])
        record = TaskRecord(
            task_number=task_number,
            path=path,
            function=function,
            task_type=task_type,
            harm=task.get("harm"),
        )
        grouped.setdefault(function, {"harmful": [], "benign": []})
        grouped[function][task_type].append(record)
    
    # Process multi-turn tasks
    multi_turn_tasks = data.get("multi_turn_tasks", {}).get("tasks", [])
    
    for task in multi_turn_tasks:
        task_name = task.get("task_name", "")
        # Extract task number from task_name (e.g., "multi_turn_task.5" -> 105)
        # Use 100+ offset to distinguish from single-turn tasks
        try:
            base_number = int(task_name.split(".")[-1])
            task_number = 100 + base_number  # e.g., multi_turn_task.5 -> 105
        except ValueError:
            continue
        
        function = task.get("function", "unknown_function")
        
        # Get type and harm from the original single-turn task if available
        original_task = task.get("original_task", "")
        original_info = single_turn_lookup.get(original_task, {})
        task_type = original_info.get("type", "harmful")
        harm = original_info.get("harm")
        
        path = Path(task["path"])
        record = TaskRecord(
            task_number=task_number,
            path=path,
            function=function,
            task_type=task_type,
            harm=harm,
        )
        grouped.setdefault(function, {"harmful": [], "benign": []})
        grouped[function][task_type].append(record)
    
    for bucket in grouped.values():
        bucket["harmful"].sort(key=lambda r: r.task_number)
        bucket["benign"].sort(key=lambda r: r.task_number)
    
    return grouped




@contextmanager
def temporary_experience_file(
    experiences: Dict[str, str],
    reference_path: Path
):
    """Write experiences to a temporary file for experimentation."""
    reference_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        prefix="exp_tmp_", suffix=".json", dir=reference_path.parent, delete=False
    ) as tmp:
        tmp_path = Path(tmp.name)
    save_experience_list(experiences, tmp_path)
    try:
        yield tmp_path
    finally:
        try:
            tmp_path.unlink()
        except FileNotFoundError:
            pass


def run_shell(cmd: str) -> None:
    """Execute a shell command without raising on failure."""
    subprocess.run(cmd, shell=True, check=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run exploration tasks sequentially with iterative experience updates."
    )
    parser.add_argument(
        "--task-root", 
        type=Path, 
        default=DEFAULT_TASK_ROOT, 
        help="Directory containing task.* folders."
    )
    parser.add_argument(
        "--output-dir", 
        type=Path, 
        default=DEFAULT_OUTPUT_DIR, 
        help="Directory to store run_eval outputs."
    )
    parser.add_argument(
        "--experience-file", 
        type=Path, 
        default=DEFAULT_EXPERIENCE_FILE, 
        help="Path to the shared experience JSON."
    )
    parser.add_argument(
        "--agent-llm-config", 
        default="agent", 
        help="Agent LLM config name (matches run_eval.py)."
    )
    parser.add_argument(
        "--agent-llm-config-file", 
        default="agent_config/config.toml", 
        help="Agent LLM config file path."
    )
    parser.add_argument(
        "--env-llm-config", 
        default="env", 
        help="Env LLM config name (matches run_eval.py)."
    )
    parser.add_argument(
        "--env-llm-config-file", 
        default="agent_config/config_mcp.toml", 
        help="Env LLM config file path."
    )
    parser.add_argument(
        "--server-hostname", 
        default=os.environ.get("SERVER_HOST", "localhost"), 
        help="Remote runtime hostname (default: $REMOTE_HOST or localhost)."
    )
    parser.add_argument(
        "--remote-hostname", 
        default=None, 
        help="Alias for server hostname (if set overrides --server-hostname)."
    )
    parser.add_argument(
        "--eval-dir", 
        type=Path, 
        default=DEFAULT_EVAL_DIR, 
        help="Directory that contains run_eval.py."
    )
    parser.add_argument(
        "--max-attempts", 
        type=int, 
        default=3, 
        help="Max retries per task if run_eval fails."
    )
    parser.add_argument(
        "--poetry-bin", 
        default="poetry", 
        help="Poetry executable name/path."
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output with detailed experience updates."
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Show full execution logs (including OpenHands output)."
    )
    parser.add_argument(
        "--truncate-trajectory",
        action="store_true",
        help="Truncate long trajectories to fit within LLM context limits."
    )
    parser.add_argument(
        "--max-trajectory-tokens",
        type=int,
        default=150000,
        help="Maximum tokens for trajectory when truncation is enabled (default: 150000)."
    )
    return parser.parse_args()


def cleanup_runtime_artifacts() -> None:
    """Mirror run_single_turn_tasks.sh cleanup routine with process killing."""
    print("  🧹 Cleaning up OpenHands runtime containers and volumes...")
    
    # 1. Kill container processes first
    run_shell(
        "docker ps -q --filter 'name=openhands-runtime' | "
        "xargs -r docker inspect --format '{{.State.Pid}}' 2>/dev/null | "
        "xargs -r sudo kill -9 2>/dev/null || true"
    )
    
    # 2. Wait for processes to exit
    time.sleep(2)
    
    # 3. Remove containers
    run_shell("docker ps -a --filter 'name=openhands-runtime' -q | xargs -r docker rm -f 2>/dev/null || true")
    
    # 4. Prune volumes
    run_shell("docker volume prune -f")
    
    print("  ✅ Cleanup completed")


def remove_runtime_images() -> None:
    """Remove cached runtime images similar to the shell script."""
    run_shell("docker images | awk '/ghcr.io\\/all-hands-ai\\/runtime/ {print $3}' | xargs -r docker rmi -f")
    run_shell("docker images | grep ghcr.io/all-hands-ai/runtime || true")


def run_task(
    task_dir: Path,
    base_cmd: list[str],
    workdir: Path,
    experience_file: Path,
    max_attempts: int,
    debug: bool = False,
) -> Tuple[bool, Optional[Path]]:
    """Execute a single task using run_eval.py."""
    cmd = base_cmd + ["--task-path", str(task_dir.resolve())]
    if experience_file.exists():
        cmd += ["--use-experience", str(experience_file)]

    for attempt in range(1, max_attempts + 1):
        if debug:
            print(f"  [Attempt {attempt}/{max_attempts}] Running task evaluation...")
        try:
            env = os.environ.copy()
            env.pop("LOGPROB_TAG", None)
            if debug:
                subprocess.run(cmd, check=True, cwd=workdir, env=env)
                print("  ✓ Task evaluation succeeded")
            else:
                with open(os.devnull, "wb") as devnull:
                    subprocess.run(
                        cmd,
                        check=True,
                        cwd=workdir,
                        env=env,
                        stdout=devnull,
                        stderr=devnull,
                    )
            return True, None
        except subprocess.CalledProcessError as exc:
            if debug:
                print(f"  ✗ Task evaluation failed (exit {exc.returncode})")
    
    if debug:
        print("  ✗ Exceeded retry budget; skipping task")
    return False, None


def run_task_with_cleanup(
    task_dir: Path,
    base_cmd: list[str],
    workdir: Path,
    experience_file: Path,
    max_attempts: int,
    outputs_dir: Path,
    run_counters: Dict[Tuple[int, str], int],
    label: str,
    debug: bool = False,
) -> Tuple[bool, Optional[Path]]:
    """Run a task and perform cleanup regardless of outcome."""
    success, logprob_path = run_task(
        task_dir,
        base_cmd,
        workdir,
        experience_file,
        max_attempts,
        debug=debug,
    )
    archive_task_state(task_dir, outputs_dir, run_counters, label)
    cleanup_runtime_artifacts()
    remove_runtime_images()
    return success, logprob_path


def run_task_with_experience_dict(
    task_dir: Path,
    base_cmd: list[str],
    workdir: Path,
    experience_dict: Dict[str, str],
    args: argparse.Namespace,
    run_counters: Dict[Tuple[int, str], int],
    label: str,
) -> Tuple[bool, Optional[Path]]:
    """Run a task using a temporary experience file derived from a dict."""
    with temporary_experience_file(experience_dict, args.experience_file) as temp_exp:
        return run_task_with_cleanup(
            task_dir=task_dir,
            base_cmd=base_cmd,
            workdir=workdir,
            experience_file=temp_exp,
            max_attempts=args.max_attempts,
            outputs_dir=args.output_dir,
            run_counters=run_counters,
            label=label,
            debug=args.debug,
        )


def main() -> None:
    args = parse_args()

    task_root = args.task_root
    if not task_root.exists():
        raise FileNotFoundError(f"Task root not found: {task_root}")

    summary_path = task_root / "generation_summary.json"
    grouped_tasks = load_generation_summary(summary_path)
    if not grouped_tasks:
        print("No tasks described in generation_summary.json")
        return

    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.experience_file.parent.mkdir(parents=True, exist_ok=True)

    # Build base command for run_eval.py
    hostname = args.remote_hostname or args.server_hostname
    base_cmd = [
        args.poetry_bin,
        "run",
        "python",
        "run_eval.py",
        "--agent-llm-config",
        args.agent_llm_config,
        "--agent-llm-config-file",
        args.agent_llm_config_file,
        "--env-llm-config",
        args.env_llm_config,
        "--env-llm-config-file",
        args.env_llm_config_file,
        "--outputs-path",
        str(args.output_dir),
        "--server-hostname",
        hostname,
    ]

    # Load Initial Experience Pool
    experiences = load_experience_list(args.experience_file)
    save_experience_list(experiences, args.experience_file)

    if args.debug:
        print("=" * 70)
        print("Sequential Task Execution")
        print("=" * 70)
        print(f"Functions discovered: {len(grouped_tasks)}")
        print(f"Experience file: {args.experience_file}")
    else:
        print("[4/4] Processing Tasks")

    # Prepare Tasks
    task_to_function: Dict[int, str] = {}
    harmful_lookup: Dict[int, TaskRecord] = {}
    
    for func_name, suite in grouped_tasks.items():
        for harmful_task in suite["harmful"]:
            task_to_function[harmful_task.task_number] = func_name
            harmful_lookup[harmful_task.task_number] = harmful_task
    
    all_harmful_tasks = sorted(
        task_to_function.keys(),
        key=lambda x: (0 if x >= 100 else 1, x)
    )
    run_counters: Dict[Tuple[int, str], int] = {}
    selection_count = 0
    current_function = None

    total_tasks = len(all_harmful_tasks)
    task_iter = enumerate(all_harmful_tasks, 1)
    if not args.debug:
        task_iter = tqdm(
            task_iter,
            total=total_tasks,
            desc="Processing tasks",
            unit="task",
        )
    for index, task_num in task_iter:
        function_name = task_to_function[task_num]
        if function_name != current_function:
            current_function = function_name
            if args.debug:
                print(f"\n{'=' * 70}")
                print(f"Function: {function_name}")
                print("=" * 70)

        harmful_task = harmful_lookup[task_num]
        if args.debug:
            print(f"\n  → Processing harmful task.{harmful_task.task_number} ({harmful_task.harm})")
        # Execute task to generate trace
        save_experience_list(experiences, args.experience_file)
        run_task_with_cleanup(
            harmful_task.path,
            base_cmd,
            args.eval_dir,
            args.experience_file,
            args.max_attempts,
            outputs_dir=args.output_dir,
            run_counters=run_counters,
            label=f"{task_num}_run1",
            debug=args.debug,
        )

        # Generate experience from trace
        result = learn_from_task_state(harmful_task.task_number)
        try:
            updated_exps, metadata = apply_experience_result(experiences, result)
        except ValueError as exc:
            if args.verbose:
                print(f"    ○ Skipped: {exc}")
            continue

        if not metadata.get("changed", False):
            if args.debug:
                print(f"    ○ No experience improvement found for Task {task_num}.")
            continue

        experiences = updated_exps
        save_experience_list(experiences, args.experience_file)
        selection_count += 1
        if args.debug:
            print(f"    ★ Updated Experience Pool with {metadata.get('target_key')}")

    if args.debug:
        print(f"\n{'=' * 70}")
        print("Execution Summary")
        print('=' * 70)
        print(f"Functions processed: {len(grouped_tasks)}")
        print(f"Experiences selected: {selection_count}")
        print(f"Experience library: {args.experience_file}")
        print('=' * 70)


if __name__ == "__main__":
    main()

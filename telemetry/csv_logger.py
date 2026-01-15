"""
CSV Logger for Evaluation Results

Logs evaluation metrics and statistics to CSV file for analysis.
"""

import csv
import os
from typing import List, Dict, Any
from pathlib import Path


class CSVLogger:
    """Logs evaluation results to CSV file"""

    @staticmethod
    def extract_statistics(agent_history: List[Dict[str, Any]]) -> Dict[str, int]:
        """Extract tool usage statistics from agent_history

        Args:
            agent_history: List of ReAct iteration entries

        Returns:
            Dictionary with statistics:
            - tool_creation_attempts
            - tool_creation_successes
            - tool_execution_attempts_total
            - tool_execution_attempts_safe
            - tool_execution_attempts_sandbox
            - tool_execution_successes_total
            - tool_execution_successes_safe
            - tool_execution_successes_sandbox
            - tool_fix_attempts
            - tool_fix_successes
            - error_encountered (0 or 1)
            - recovered (0 or 1, only meaningful if error_encountered=1)
        """
        stats = {
            'tool_creation_attempts': 0,
            'tool_creation_successes': 0,
            'tool_execution_attempts_total': 0,
            'tool_execution_attempts_safe': 0,
            'tool_execution_attempts_sandbox': 0,
            'tool_execution_successes_total': 0,
            'tool_execution_successes_safe': 0,
            'tool_execution_successes_sandbox': 0,
            'tool_fix_attempts': 0,
            'tool_fix_successes': 0,
            'error_encountered': 0,
            'recovered': 0
        }

        error_found = False

        for entry in agent_history:
            action = entry.get('action', '')
            action_result = entry.get('action_result', {})
            action_input = entry.get('action_input', {})
            success = action_result.get('success', False)

            # Track errors
            if not success:
                error_found = True

            # Tool creation
            if action == 'create_ifc_tool':
                stats['tool_creation_attempts'] += 1
                if success:
                    stats['tool_creation_successes'] += 1

            # Tool execution
            elif action == 'execute_ifc_tool':
                execution_mode = action_input.get('execution_mode', 'safe')
                stats['tool_execution_attempts_total'] += 1

                if execution_mode == 'safe':
                    stats['tool_execution_attempts_safe'] += 1
                    if success:
                        stats['tool_execution_successes_safe'] += 1
                elif execution_mode == 'sandbox':
                    stats['tool_execution_attempts_sandbox'] += 1
                    if success:
                        stats['tool_execution_successes_sandbox'] += 1

                if success:
                    stats['tool_execution_successes_total'] += 1

            # Tool fixing
            elif action == 'fix_ifc_tool':
                stats['tool_fix_attempts'] += 1
                if success:
                    stats['tool_fix_successes'] += 1

        stats['error_encountered'] = 1 if error_found else 0

        # Calculate empty tool executions
        empty_execution_count = 0
        for entry in agent_history:
            action = entry.get('action', '')
            action_result = entry.get('action_result', {})
            success = action_result.get('success', False)

            if action == 'execute_ifc_tool' and success:
                result_data = action_result.get('result', {})
                ifc_result = result_data.get('result')

                # Check if result is empty
                if ifc_result in (None, {}, [], ""):
                    empty_execution_count += 1

        stats['empty_tool_executions'] = empty_execution_count

        return stats

    @staticmethod
    def log_to_csv(
        csv_path: str,
        sample_id: str,
        regulation_id: str,
        model_id: str,
        weighted_f1: float,
        macro_f1: float,
        correctness: bool,
        iterations: int,
        runtime: float,
        statistics: Dict[str, int],
        final_state: str
    ):
        """Append evaluation result to CSV file

        Args:
            csv_path: Path to CSV file
            sample_id: Sample identifier
            regulation_id: Regulation identifier (e.g., R-Dev-01)
            model_id: Model identifier (e.g., M01)
            weighted_f1: Weighted F1 score
            macro_f1: Macro-averaged F1 score
            correctness: Whether prediction is correct (hybrid criterion)
            iterations: Number of ReAct iterations used
            runtime: Runtime in seconds
            statistics: Dictionary from extract_statistics()
            final_state: "success", "failure", or "timeout"
        """
        csv_file = Path(csv_path)

        # Determine if file exists and if header is needed
        file_exists = csv_file.exists()

        # Ensure parent directory exists
        csv_file.parent.mkdir(parents=True, exist_ok=True)

        # Determine if recovered (only meaningful if error occurred)
        recovered = 0
        if statistics['error_encountered'] == 1 and final_state == 'success':
            recovered = 1

        # Define CSV columns
        fieldnames = [
            'sample_id',
            'regulation_id',
            'model_id',
            'weighted_f1',
            'macro_f1',
            'correctness',
            'iterations',
            'total_subgoals',
            'runtime',
            'tool_creation_attempts',
            'tool_creation_successes',
            'tool_execution_attempts_total',
            'tool_execution_attempts_safe',
            'tool_execution_attempts_sandbox',
            'tool_execution_successes_total',
            'tool_execution_successes_safe',
            'tool_execution_successes_sandbox',
            'empty_tool_executions',
            'tool_fix_attempts',
            'tool_fix_successes',
            'error_encountered',
            'recovered',
            'final_state'
        ]

        # Prepare row data
        row = {
            'sample_id': sample_id,
            'regulation_id': regulation_id,
            'model_id': model_id,
            'weighted_f1': f"{weighted_f1:.3f}",
            'macro_f1': f"{macro_f1:.3f}",
            'correctness': int(correctness),
            'iterations': iterations,
            'total_subgoals': statistics.get('total_subgoals', 0),
            'runtime': f"{runtime:.2f}",
            'tool_creation_attempts': statistics['tool_creation_attempts'],
            'tool_creation_successes': statistics['tool_creation_successes'],
            'tool_execution_attempts_total': statistics['tool_execution_attempts_total'],
            'tool_execution_attempts_safe': statistics['tool_execution_attempts_safe'],
            'tool_execution_attempts_sandbox': statistics['tool_execution_attempts_sandbox'],
            'tool_execution_successes_total': statistics['tool_execution_successes_total'],
            'tool_execution_successes_safe': statistics['tool_execution_successes_safe'],
            'tool_execution_successes_sandbox': statistics['tool_execution_successes_sandbox'],
            'empty_tool_executions': statistics.get('empty_tool_executions', 0),
            'tool_fix_attempts': statistics['tool_fix_attempts'],
            'tool_fix_successes': statistics['tool_fix_successes'],
            'error_encountered': statistics['error_encountered'],
            'recovered': recovered,
            'final_state': final_state
        }

        # Write to CSV
        with open(csv_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)

            # Write header if file is new
            if not file_exists or csv_file.stat().st_size == 0:
                writer.writeheader()

            writer.writerow(row)

        print(f"[CSV Logger] Logged results to {csv_path}")

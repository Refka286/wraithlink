import ast

# adapters store parsed findings as str(dict) (see app/tasks/run_action.py) -
# shared by the PDF report and the CSV/JSON export so both render the same
# readable "key: value" line instead of the raw Python repr, dropping the
# type/severity keys since those are already shown in their own columns


def format_finding_description(raw_description: str) -> str:
    try:
        parsed = ast.literal_eval(raw_description)
    except (ValueError, SyntaxError):
        return raw_description

    if not isinstance(parsed, dict):
        return raw_description

    parts = [f"{key}: {value}" for key, value in parsed.items() if key not in {"type", "severity"} and value is not None]
    return " | ".join(parts) if parts else raw_description

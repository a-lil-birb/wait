def show_diff(original: str, modified: str) -> str:
    """Simple diff visualizer"""
    from difflib import ndiff
    
    diff = list(ndiff(original.splitlines(), modified.splitlines()))
    return "\n".join([
        f"{line[0]} | {line[2:]}"
        for line in diff
        if not line.startswith(' ')
    ])
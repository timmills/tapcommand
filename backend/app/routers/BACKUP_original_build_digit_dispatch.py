# BACKUP - Original _build_digit_dispatch() function
# Saved before implementing array-based optimization
# Date: 2025-10-01
#
# This is the NESTED PYRAMID approach that creates ~504 lines of deeply nested if/else
#
# To restore: Copy this function back into templates.py at line 970

def _build_digit_dispatch() -> List[str]:
    """
    Original implementation using nested if/else pyramid.
    Creates deeply nested structure (10+ levels) for port/digit combinations.
    Results in ~504 lines for dispatch_digit script.
    """
    block: List[str] = [
        "- id: dispatch_digit",
        "  parameters:",
        "    target_port: int",
        "    digit: int",
        "  then:",
    ]

    if not assigned_ports:
        block.extend([
            "    - logger.log:",
            "        level: WARN",
            "        format: \"No ports configured for digit command\"",
        ])
        return block

    entries: List[Tuple[str, List[str]]] = []
    for port in assigned_ports:
        profile = assigned_port_map[port]
        digit_entries: List[Tuple[str, List[str]]] = []
        digit_keys = sorted(int(key.split('_')[1]) for key in profile.commands if key.startswith('number_'))
        for digit in digit_keys:
            key = f"number_{digit}"
            spec = profile.commands.get(key)
            if spec:
                actions = _render_transmit_lines(spec, port)
            else:
                actions = _render_missing_command_lines(port, key)
            digit_entries.append((f"digit == {digit}", actions))

        if digit_entries:
            port_actions = _build_nested_if(digit_entries, f"Port {port} digit %d unsupported", "digit")
        else:
            port_actions = _render_missing_command_lines(port, "digit")

        entries.append((f"target_port == {port}", port_actions))

    nested = _build_nested_if(entries, "Port %d unsupported for digit command", "target_port")
    block.extend(_indent(nested, 4))

    return block


# OPTIMIZATION NOTES:
#
# Problems with this approach:
# 1. Creates pyramid of nested if/else statements 10+ levels deep
# 2. Generates ~504 lines of repetitive YAML
# 3. Slow to compile due to deep nesting
# 4. Hard to read and maintain
# 5. O(n) conditional chain performance
#
# The new array-based approach fixes all of these:
# - Flat structure (1 level deep)
# - Only ~60 lines of YAML (88% reduction)
# - Faster compilation
# - Easy to read (all codes visible at once)
# - O(1) array lookup performance

from dataclasses import dataclass, field


@dataclass
class _RobotsBlock:
    user_agents: list[str] = field(default_factory=list)
    allow: list[str] = field(default_factory=list)
    disallow: list[str] = field(default_factory=list)


def _parse_robots_txt(robots_txt: str) -> list[_RobotsBlock]:
    blocks: list[_RobotsBlock] = []
    current = _RobotsBlock()
    for raw_line in robots_txt.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, value = [part.strip() for part in line.split(":", 1)]
        key_lower = key.lower()
        if key_lower == "user-agent":
            if current.user_agents and (current.allow or current.disallow):
                blocks.append(current)
                current = _RobotsBlock()
            current.user_agents.append(value.lower())
        elif key_lower == "allow":
            current.allow.append(value)
        elif key_lower == "disallow":
            current.disallow.append(value)
    if current.user_agents:
        blocks.append(current)
    return blocks


def is_path_allowed_by_robots(robots_txt: str, path: str, user_agent: str = "*") -> bool:
    blocks = _parse_robots_txt(robots_txt)
    user_agent = user_agent.lower()
    matching = [block for block in blocks if user_agent in block.user_agents or "*" in block.user_agents]
    if not matching:
        return True
    matched = matching[-1]
    for allow_rule in matched.allow:
        if allow_rule and path.startswith(allow_rule):
            return True
    for disallow_rule in matched.disallow:
        if disallow_rule and path.startswith(disallow_rule):
            return False
    return True


"""Generate the tiny independent UI palette from checked-in TOML."""
import sys
import tomllib
from pathlib import Path


def main() -> None:
    data = tomllib.loads(Path(__file__).with_name("theme.toml").read_text())
    lines = ["#pragma once", "namespace beatstyle {"]
    for name, value in data.items():
        if not name.isidentifier() or not isinstance(value, str) or len(value) != 6:
            raise ValueError("Expected six-digit theme colors")
        int(value, 16)
        lines.append(f"inline constexpr unsigned {name} = 0xff{value};")
    lines.append("}")
    Path(sys.argv[1]).write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()

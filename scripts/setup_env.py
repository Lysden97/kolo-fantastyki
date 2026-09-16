"""Create a local .env without displaying secrets or overwriting existing configuration."""

import secrets
from pathlib import Path

root = Path(__file__).resolve().parent.parent
target = root / ".env"
content = (root / ".env.example").read_text(encoding="utf-8")
content = content.replace("SECRET_KEY=\n", f"SECRET_KEY={secrets.token_urlsafe(64)}\n")
content = content.replace(
    "DATABASE_PASSWORD=\n", f"DATABASE_PASSWORD={secrets.token_urlsafe(32)}\n"
)
try:
    with target.open("x", encoding="utf-8", newline="\n") as output:
        output.write(content)
except FileExistsError:
    raise SystemExit(".env already exists; it has not been modified.") from None
print("Created .env with random local credentials. Never commit this file.")

"""Single-service test deployment: migrate, then serve on the hosting platform's port."""

import os
import subprocess


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    if not 1 <= port <= 65535:
        raise SystemExit("PORT must be between 1 and 65535.")
    subprocess.run(["alembic", "upgrade", "head"], check=True)
    os.execvp("uvicorn", ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", str(port)])

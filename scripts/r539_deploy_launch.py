"""R539 deploy launcher: loads session credentials from a vault file
outside the repo into env, then runs the deploy driver. Credential
values never appear on any command line, in any log, or in git."""
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
_DEFAULT_VAULT = r"C:\Users\ADMINI~1\AppData\Local\Temp\opencode\r539_vault.env"
VAULT = Path(os.environ.get("R539_VAULT", "") or _DEFAULT_VAULT)


def main() -> int:
    if not VAULT or not VAULT.exists():
        print("FATAL: R539_VAULT vault file absent")
        return 2
    for line in VAULT.read_text().splitlines():
        line = line.strip()
        if line and "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()
    for k in ("HF_TOKEN", "AGNES_API_KEY", "GITHUB_PAT"):
        if not os.environ.get(k):
            print(f"FATAL: {k} absent from vault")
            return 2
    sys.path.insert(0, str(REPO / "scripts"))
    import r539_space_deploy
    return r539_space_deploy.main()


if __name__ == "__main__":
    sys.exit(main())

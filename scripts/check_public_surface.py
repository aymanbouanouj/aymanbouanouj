#!/usr/bin/env python3
"""Additional fail-closed check for obviously sensitive tracked file paths."""
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PROTECTED={".npmrc",".pypirc",".netrc","id_rsa","id_ed25519","id_ecdsa","credentials.json","service-account.json","service_account.json","secrets.json","secrets.yml","secrets.yaml","secrets.toml"}
EXTENSIONS=(".pem",".p12",".pfx",".kdbx",".keystore",".jks",".sqlite",".sqlite3",".db",".dump",".tfstate",".tfstate.backup",".env.local",".env.production",".age")
DIRECTORIES={".aws",".ssh",".gnupg",".kube"}
def audit():
    paths=subprocess.run(["git","-C",str(ROOT),"ls-files","-z"],check=True,capture_output=True).stdout.decode().split("\0")
    bad=[]
    for path in filter(None,paths):
        parts=path.lower().split("/")
        filename=parts[-1]
        if (filename in PROTECTED or filename.endswith(EXTENSIONS)
                or any(p in DIRECTORIES for p in parts)
                or (filename.startswith(".env") and filename!=".env.example")):
            bad.append(path)
    if bad: raise ValueError("Sensitive tracked filenames found: "+", ".join(bad))
    notice=(ROOT/"NOTICE.md").read_text(encoding="utf-8")
    assert "All rights reserved" in notice and "Tous droits réservés" in notice
    assert "/ @aymanbouanouj" in (ROOT/".github/CODEOWNERS").read_text(encoding="utf-8")
    print(f"PASS: {len(list(filter(None, paths)))} tracked file paths reviewed; owner notice present")
if __name__=="__main__":
    try: audit()
    except (ValueError,OSError,AssertionError,subprocess.CalledProcessError) as e:
        print(f"FAIL: {e}",file=sys.stderr)
        sys.exit(1)

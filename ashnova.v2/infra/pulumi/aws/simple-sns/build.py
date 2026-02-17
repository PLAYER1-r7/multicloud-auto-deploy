import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

repo_root = Path(__file__).resolve().parents[4]
api_source_dir = repo_root / "services" / "simple_sns_api"
build_dir = Path(__file__).resolve().parent / ".build" / "simple_sns_api"
zip_path = build_dir / "lambda.zip"

lambda_python_version = "3.12"
lambda_platform = "manylinux2014_aarch64"


def build_lambda_package() -> Path:
    if not api_source_dir.exists():
        raise FileNotFoundError(f"API source not found: {api_source_dir}")

    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True, exist_ok=True)

    shutil.copytree(api_source_dir / "app", build_dir / "app")
    shutil.copy(api_source_dir / "handler.py", build_dir / "handler.py")

    subprocess.check_call(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-r",
            str(api_source_dir / "requirements.txt"),
            "-t",
            str(build_dir),
            "--platform",
            lambda_platform,
            "--python-version",
            lambda_python_version,
            "--implementation",
            "cp",
            "--abi",
            "cp312",
            "--only-binary=:all:",
        ]
    )

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in build_dir.rglob("*"):
            if path.is_file() and path != zip_path:
                zf.write(path, path.relative_to(build_dir))

    return zip_path

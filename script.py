import ast
import io
import json
import zipfile
from pathlib import Path

BASE_URL = "https://raw.githubusercontent.com/MxUserBot/mx-modules/main/modules"

SKIP_DIRS = {"__pycache__"}
SKIP_EXTS = {".pyc", ".pyo"}
SKIP_FILES = {"__pycache__"}


def extract_value(node):
    try:
        return ast.literal_eval(node)
    except Exception:
        return None


def extract_meta(source: str, default_url: str) -> dict | None:
    try:
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError):
        return None

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "Meta":
            meta = {
                "url": default_url,
                "author": "Unknown",
                "dependencies": [],
                "tags": [],
            }
            mapping = {
                "name": "name",
                "description": "description",
                "version": "version",
                "dependencies": "dependencies",
                "tags": "tags",
                "author": "author",
            }
            for item in node.body:
                if isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name) and target.id in mapping:
                            val = extract_value(item.value)
                            if val is not None:
                                meta[mapping[target.id]] = val
            return meta
    return None


def package_folder(folder: Path) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in folder.rglob("*"):
            if path.is_dir():
                continue
            rel = path.relative_to(folder.parent)
            if path.name in SKIP_FILES or path.suffix in SKIP_EXTS:
                continue
            if any(part in SKIP_DIRS for part in path.relative_to(folder).parts):
                continue
            zf.write(path, str(rel))
    return buf.getvalue()


def generate_index():
    folder_name = BASE_URL.rstrip("/").split("/")[-1]
    modules_dir = Path(folder_name)

    index_data = {}

    if not modules_dir.exists() or not modules_dir.is_dir():
        return

    # --- single .py files ---
    for file in sorted(modules_dir.glob("*.py")):
        if file.name.startswith("_"):
            continue

        meta = extract_meta(file.read_text("utf-8"), f"{BASE_URL.rstrip('/')}/{file.name}")
        if meta:
            index_data[file.stem] = meta
            print(f"✅ | Indexed: {file.stem}")
        else:
            print(f"⚠️ | Skipped: {file.name}")

    # --- folder modules ---
    for folder in sorted(modules_dir.iterdir()):
        if not folder.is_dir() or folder.name.startswith("_") or folder.name in SKIP_DIRS:
            continue

        init_file = folder / "__init__.py"
        if not init_file.exists():
            print(f"⚠️ | Skipped folder (no __init__.py): {folder.name}/")
            continue

        zip_name = f"{folder.name}.zip"
        zip_path = modules_dir / zip_name

        source = init_file.read_text("utf-8")
        meta = extract_meta(source, f"{BASE_URL.rstrip('/')}/{zip_name}")
        if not meta:
            print(f"⚠️ | Skipped folder (no Meta): {folder.name}/")
            continue

        data = package_folder(folder)
        zip_path.write_bytes(data)
        index_data[folder.name] = meta
        print(f"✅ | Packed & indexed: {folder.name}/ → {zip_name}")

    output_file = Path("index.json")
    output_file.write_text(
        json.dumps(index_data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\n📦 | index.json written ({len(index_data)} entries)")


if __name__ == "__main__":
    try:
        generate_index()
    except Exception as e:
        raise e
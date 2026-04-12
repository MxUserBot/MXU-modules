import ast
import json
from pathlib import Path


def extract_value(node):
    try:
        return ast.literal_eval(node)
    except Exception:
        return None


def extract_module_meta(path: Path):
    source = path.read_text("utf-8")
    tree = ast.parse(source)

    meta = None

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "Meta":
            meta = {
                "id": path.stem,
                "path": path.name,
                "commands": []
            }

            for item in node.body:
                if isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name):
                            key = target.id
                            value = extract_value(item.value)

                            if value is None:
                                continue

                            if key == "name":
                                meta["name"] = value
                            elif key in ("description", "_cls_doc"):
                                meta["description"] = value
                            elif key == "version":
                                meta["version"] = value
                            elif key == "dependencies":
                                meta["dependencies"] = value
                            elif key == "tags":
                                meta["tags"] = value

            break

    if meta is None:
        print(f"[SKIP] {path.name}: no Meta class")
        return None

    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef):
            for dec in node.decorator_list:
                if isinstance(dec, ast.Call):
                    if isinstance(dec.func, ast.Attribute):
                        if dec.func.attr == "command":
                            meta["commands"].append(node.name)

    if not meta["commands"]:
        del meta["commands"]

    return meta



modules_dir = Path("modules")
modules = []

if modules_dir.exists() and modules_dir.is_dir():
    for file in modules_dir.glob("*.py"):
        if file.name.startswith("_"):
            continue

        module_meta = extract_module_meta(file)
        if module_meta is not None:
            modules.append(module_meta)

# Записываем результат
Path("index.json").write_text(
    json.dumps({"modules": modules}, indent=2, ensure_ascii=False),
    encoding="utf-8"
)

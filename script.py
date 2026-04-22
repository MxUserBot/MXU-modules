import ast
import json
from pathlib import Path

BASE_URL = "https://raw.githubusercontent.com/PashaHatsune/MxUserbot/main/modules"


def extract_value(node):
    try:
        return ast.literal_eval(node)
    except Exception:
        return None


def generate_index():
    modules_dir = Path("modules")
    index_data = {}

    if not modules_dir.exists():
        print("Fo;der not found.")
        return

    for file in modules_dir.glob("*.py"):
        if file.name.startswith("_"):
            continue

        source = file.read_text("utf-8")
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue

        meta_info = None

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "Meta":
                meta_info = {
                    "url": f"{BASE_URL}/{file.name}",
                    "author": "Unknown",
                    "dependencies": [],
                    "tags": []
                }
                
                for item in node.body:
                    if isinstance(item, ast.Assign):
                        for target in item.targets:
                            if isinstance(target, ast.Name):
                                key = target.id
                                val = extract_value(item.value)
                                if val is None: continue
                                
                                if key == "name": 
                                    meta_info["name"] = val
                                elif key in ("description", "_cls_doc"): 
                                    meta_info["description"] = val
                                elif key == "version": 
                                    meta_info["version"] = val
                                elif key == "dependencies": 
                                    meta_info["dependencies"] = val
                                elif key == "tags": 
                                    meta_info["tags"] = val
                                elif key == "author":
                                    meta_info["author"] = val
                break

        if meta_info:
            index_data[file.stem] = meta_info
            print(f"✅ | Indexed: {file.stem}")
        else:
            print(f"⚠️ | Skipped: {file.name} (No class Meta)")

    Path("index.json").write_text(
        json.dumps(index_data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    print(f"\nDONE | Indexed: {len(index_data)}")


if __name__ == "__main__":
    generate_index()
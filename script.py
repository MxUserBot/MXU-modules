import ast
import json
from pathlib import Path

BASE_URL = "https://raw.githubusercontent.com/MxUserBot/mx-modules/main/modules"


def extract_value(node):
    try:
        return ast.literal_eval(node)
    except Exception:
        return None

def generate_index():
    folder_name = BASE_URL.rstrip("/").split("/")[-1]
    modules_dir = Path(folder_name)
    
    index_data = {}

    if not modules_dir.exists() or not modules_dir.is_dir():
        return


    for file in modules_dir.glob("*.py"):
        if file.name.startswith("_"):
            continue

        try:
            source = file.read_text("utf-8")
            tree = ast.parse(source)
        except (SyntaxError, UnicodeDecodeError):
            continue

        meta_info = None

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "Meta":
                meta_info = {
                    "url": f"{BASE_URL.rstrip('/')}/{file.name}",
                    "author": "Unknown",
                    "dependencies": [],
                    "tags": []
                }
                
                mapping = {
                    "name": "name",
                    "description": "description",
                    "version": "version",
                    "dependencies": "dependencies",
                    "tags": "tags",
                    "author": "author"
                }

                for item in node.body:
                    if isinstance(item, ast.Assign):
                        for target in item.targets:
                            if isinstance(target, ast.Name) and target.id in mapping:
                                val = extract_value(item.value)
                                if val is not None:
                                    meta_info[mapping[target.id]] = val
                break

        if meta_info:
            index_data[file.stem] = meta_info
            print(f"✅ | Indexed: {file.stem}")
        else:
            print(f"⚠️ | Skipped: {file.name}")

    output_file = Path("index.json")
    output_file.write_text(
        json.dumps(index_data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

if __name__ == "__main__":
    try:
        generate_index()
    except Exception as e:
        raise e
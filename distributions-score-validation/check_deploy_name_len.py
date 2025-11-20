#!/usr/bin/env python3
import os
import sys

try:
    import yaml  # pip install pyyaml
except ImportError:
    print("Instale o PyYAML: pip install pyyaml")
    sys.exit(1)

MAX_LEN = 63

def check_dir(base_dir: str):
    problema_encontrado = False

    for entry in sorted(os.listdir(base_dir)):
        dir_path = os.path.join(base_dir, entry)
        if not os.path.isdir(dir_path):
            continue

        yaml_path = os.path.join(dir_path, f"{entry}.yaml")
        if not os.path.isfile(yaml_path):
            # sem o arquivo com mesmo nome da pasta, ignora
            continue

        with open(yaml_path, "r") as f:
            try:
                docs = list(yaml.safe_load_all(f))
            except yaml.YAMLError as e:
                print(f"[ERRO YAML] {yaml_path}: {e}")
                continue

        for doc in docs:
            if not isinstance(doc, dict):
                continue
            if doc.get("kind") != "Deployment":
                continue

            metadata = doc.get("metadata", {}) or {}
            name = metadata.get("name")
            if not name:
                continue

            name_len = len(name)
            if name_len > MAX_LEN:
                problema_encontrado = True
                print(f"[NOME LONGO] pasta='{entry}'")
                print(f"  deployment name: {name}")
                print(f"  comprimento: {name_len} (> {MAX_LEN})\n")

    if not problema_encontrado:
        print("Nenhum Deployment com nome > 63 caracteres encontrado.")

if __name__ == "__main__":
    # usa o diretório atual se não passar nada
    base_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    check_dir(base_dir)

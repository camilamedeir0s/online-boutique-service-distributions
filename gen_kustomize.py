#!/usr/bin/env python3
import re
import os
import sys
import yaml
from typing import List, Dict, Any

#python3 gen_kustomize.py ./kube_5e425380.yaml ./kustomization.yaml

# --- Literal block helper so Kustomize patches are written with `|`
class LiteralStr(str):
    pass

def literal_str_representer(dumper, data):
    return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')

yaml.add_representer(LiteralStr, literal_str_representer)
yaml.SafeDumper.add_representer(LiteralStr, literal_str_representer)

# ===== Standardized tokens (canonical short codes) =====
# ad, ct, rec, sh, co, cur, em, main, pay, pc
TOKEN_WEIGHTS: Dict[str, int] = {
    "ad": 117,
    "ct": 195,      # cart
    "rec": 117,     # recommendation
    "sh": 115,      # shipping
    "co": 75,       # checkout
    "cur": 173,     # currency
    "em": 50,       # email
    "main": 950,
    "pay": 35,      # payment
    "pc": 173,      # product catalog
}

# Aliases: map various spellings/old abbreviations to the canonical short codes above.
ALIASES: Dict[str, str] = {
    # canonical already
    "ad": "ad", "ct": "ct", "rec": "rec", "sh": "sh", "co": "co", "cur": "cur", "em": "em", "main": "main", "pay": "pay", "pc": "pc",
    # long forms
    "cart": "ct",
    "recommendation": "rec",
    "shipping": "sh",
    "checkout": "co",
    "currency": "cur",
    "email": "em",
    "payment": "pay",
    "productcatalog": "pc",
    "product-catalog": "pc",
    "productcatalogservice": "pc",
    # older/other abbreviations seen antes
    "recom": "rec",
    "shi": "sh",
    "curr": "cur",
    "currencysvc": "cur",
    "pcatalog": "pc",
}

PREFIX_PATTERN = re.compile(r'^(onlineboutique-)?')
HEX8 = re.compile(r'^[0-9a-f]{8}$')

def normalize_token(tok: str) -> str:
    t = tok.strip().lower()
    t = re.sub(r'[^a-z0-9]', '', t)
    return ALIASES.get(t, t)

def parse_group_tokens_from_deploy_name(name: str) -> List[str]:
    base = PREFIX_PATTERN.sub('', name)
    parts = base.split('-')
    # strip trailing hex chunks (often two of them)
    while parts and HEX8.match(parts[-1]):
        parts.pop()
    return [normalize_token(p) for p in parts if p]

def sum_weights_for_tokens(tokens: List[str]) -> int:
    return sum(TOKEN_WEIGHTS.get(t, 0) for t in tokens)

def load_yaml_docs(path: str):
    with open(path, 'r', encoding='utf-8') as f:
        return list(yaml.safe_load_all(f))

def find_deployments(documents) -> List[str]:
    names = []
    for doc in documents:
        if isinstance(doc, dict) and doc.get('kind') == 'Deployment':
            name = doc.get('metadata', {}).get('name')
            if name:
                names.append(name)
    return names

def build_patch_for_deployment(name: str, msum: int) -> Dict[str, Any]:
    cpu_mem = f'"{msum}m"'
    mem_mi = f'"{msum}Mi"'
    patch_text = f"""apiVersion: apps/v1
kind: Deployment
metadata:
  name: {name}
spec:
  template:
    spec:
      containers:
        - name: serviceweaver
          $patch: merge
          resources:
            limits:
              cpu: {cpu_mem}
              memory: {mem_mi}
            requests:
              cpu: {cpu_mem}
              memory: {mem_mi}
"""
    return {"target": {"kind": "Deployment", "name": name}, "patch": LiteralStr(patch_text)}

def build_hpa_delete_patch() -> Dict[str, Any]:
    patch_text = """$patch: delete
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: dummy
"""
    return {"target": {"kind": "HorizontalPodAutoscaler"}, "patch": LiteralStr(patch_text)}

def generate_kustomization(input_path: str, deployment_names: List[str]) -> Dict[str, Any]:
    patches = [build_hpa_delete_patch()]
    for name in deployment_names:
        tokens = parse_group_tokens_from_deploy_name(name)
        msum = sum_weights_for_tokens(tokens)
        patches.append(build_patch_for_deployment(name, msum))
    return {"resources": [os.path.basename(input_path)], "patches": patches}

def main(argv: List[str]):
    if len(argv) < 2 or len(argv) > 3:
        print("Usage: gen_kustomize.py <input-manifests.yaml> [<output-kustomization.yaml>]")
        return 2
    input_path = argv[1]
    output_path = argv[2] if len(argv) == 3 else "kustomization.yaml"
    docs = load_yaml_docs(input_path)
    dep_names = find_deployments(docs)
    kobj = generate_kustomization(input_path, dep_names)
    with open(output_path, 'w', encoding='utf-8') as f:
        yaml.safe_dump(kobj, f, sort_keys=False, width=4096, allow_unicode=True)
    print(f"Wrote {output_path} with {len(dep_names)} Deployment patches.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

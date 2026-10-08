import os
import re

bundle_path = 'static/js/admin/admin-bundle.js'
with open(bundle_path, 'r', encoding='utf-8') as f:
    bundle_code = f.read()

defined_funcs = set(re.findall(r'function\s+([a-zA-Z0-9_]+)\s*\(', bundle_code))
defined_funcs.update(re.findall(r'(?:window\.)?([a-zA-Z0-9_]+)\s*=\s*(?:function|async\s+function|\()', bundle_code))

dynamic_calls = set(re.findall(r'onclick=[\'"]([a-zA-Z0-9_]+)\(', bundle_code))
missing_dynamic = [c for c in dynamic_calls if c not in defined_funcs and c not in ['alert', 'print']]

print(f"Total funciones definidas en bundle: {len(defined_funcs)}")
print(f"Llamadas dinámicas en bundle: {len(dynamic_calls)}")
print(f"Funciones dinámicas faltantes: {missing_dynamic}")

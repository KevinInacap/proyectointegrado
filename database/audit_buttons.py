import os
import re

bundle_path = 'static/js/admin/admin-bundle.js'
with open(bundle_path, 'r', encoding='utf-8') as f:
    bundle_code = f.read()

defined_funcs = set(re.findall(r'function\s+([a-zA-Z0-9_]+)\s*\(', bundle_code))
defined_funcs.update(re.findall(r'(?:window\.)?([a-zA-Z0-9_]+)\s*=\s*(?:function|async\s+function|\()', bundle_code))

views_dir = 'templates/activities/admin'
total_buttons = 0
dead_buttons = []
missing_func_buttons = []

for root, dirs, files in os.walk(views_dir):
    for file in sorted(files):
        if not file.endswith('.html'): continue
        path = os.path.join(root, file)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        button_tags = re.finditer(r'<button\b([^>]*)>(.*?)</button>', content, re.DOTALL | re.IGNORECASE)
        for m in button_tags:
            total_buttons += 1
            attrs = m.group(1)
            inner = m.group(2).strip()
            # Clean inner tags
            inner_text = re.sub(r'<[^>]+>', '', inner).strip()
            
            onclick_m = re.search(r'onclick=["\']([^"\']+)["\']', attrs)
            bs_toggle = re.search(r'data-bs-toggle=["\']([^"\']+)["\']', attrs)
            bs_dismiss = re.search(r'data-bs-dismiss=["\']([^"\']+)["\']', attrs)
            btn_type = re.search(r'type=["\']([^"\']+)["\']', attrs)
            title_m = re.search(r'title=["\']([^"\']+)["\']', attrs)
            
            onclick = onclick_m.group(1) if onclick_m else None
            title = title_m.group(1) if title_m else inner_text
            
            if not onclick and not bs_toggle and not bs_dismiss and not (btn_type and btn_type.group(1) == 'submit'):
                dead_buttons.append((file, title, attrs[:90]))
            elif onclick:
                func_name = re.match(r'([a-zA-Z0-9_]+)\s*\(', onclick)
                if func_name:
                    fn = func_name.group(1)
                    if fn not in defined_funcs and fn not in ['print', 'stopPropagation', 'alert']:
                        missing_func_buttons.append((file, fn, onclick, title))

print(f"Total botones analizados: {total_buttons}")
print(f"\n--- BOTONES SIN ACCION NI EVENTO (Total: {len(dead_buttons)}) ---")
for f, t, a in dead_buttons:
    print(f"[{f}] Texto/Título: '{t}' | Attrs: {a.strip()}")

print(f"\n--- BOTONES CON FUNCION INEXISTENTE EN JS (Total: {len(missing_func_buttons)}) ---")
for f, fn, oc, t in missing_func_buttons:
    print(f"[{f}] Función: '{fn}' | Onclick: '{oc}' | Texto/Título: '{t}'")

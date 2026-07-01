#!/usr/bin/env python3
"""
Migra as especialidades otorrino, oftalmo, psiquiatria e ortopedia
para dentro de Clínica Médica como subcategorias.
Também atualiza assuntos.json com a nova hierarquia.
"""
import json, os

BASE = os.path.expanduser('~/hermesmed-questoes')
DATA = os.path.join(BASE, 'data')

# ─── 1. Load current data ───
with open(os.path.join(DATA, 'assuntos.json')) as f:
    assuntos = json.load(f)

with open(os.path.join(DATA, 'clinica-medica.json')) as f:
    clinica = json.load(f)

with open(os.path.join(DATA, 'assuntos-estrategia.json')) as f:
    hierarquia = json.load(f)

# ─── 2. Load specialty questions & update subarea ───
SPECIALTIES = {
    'otorrino': 'Otorrinolaringologia',
    'ortopedia': 'Ortopedia',
    'psiquiatria': 'Psiquiatria',
    'oftalmologia': 'Oftalmologia',
}

SPECIALTY_QUESTIONS = {}
for slug, nome in SPECIALTIES.items():
    path = os.path.join(DATA, f'{slug}.json')
    with open(path) as f:
        data = json.load(f)
    qs = data.get('questoes', [])
    for q in qs:
        q['area'] = 'Clínica Médica'
        q['subarea'] = nome
        q['_area_slug'] = 'clinica-medica'
        q['_subarea_orig'] = slug  # auxiliar para saber de onde veio
    SPECIALTY_QUESTIONS[slug] = qs
    print(f"  {slug}: {len(qs)} questões migradas")

# ─── 3. Build merged clinica-medica ───
all_qs = list(clinica.get('questoes', []))
existing_ids = {q['id'] for q in all_qs}

for slug, qs in SPECIALTY_QUESTIONS.items():
    for q in qs:
        if q['id'] not in existing_ids:
            all_qs.append(q)
            existing_ids.add(q['id'])

clinica['questoes'] = all_qs
with open(os.path.join(DATA, 'clinica-medica.json'), 'w') as f:
    json.dump(clinica, f, ensure_ascii=False, indent=2)
print(f"  clinica-medica.json: {len(all_qs)} questões totais")

# ─── 4. Write specialty files (empty the standalone arrays) ───
for slug in SPECIALTIES:
    path = os.path.join(DATA, f'{slug}.json')
    with open(path, 'w') as f:
        json.dump({"questoes": []}, f, ensure_ascii=False, indent=2)
    print(f"  {slug}.json: esvaziado")

# ─── 5. Update assuntos.json ───
# Compute new subcategory counts for clinica-medica
from collections import defaultdict

sub_counts = defaultdict(int)
for q in all_qs:
    if q.get('subarea'):
        sub_counts[q['subarea']] += 1

def slugify(s):
    import re
    s = s.lower().strip()
    replacements = {
        'á':'a','à':'a','â':'a','ã':'a','ä':'a',
        'é':'e','è':'e','ê':'e','ë':'e',
        'í':'i','ì':'i','î':'i','ï':'i',
        'ó':'o','ò':'o','ô':'o','õ':'o','ö':'o',
        'ú':'u','ù':'u','û':'u','ü':'u',
        'ç':'c','ñ':'n',
        '/':'-','(':'',')':'','"':'',',':'',':':''
    }
    for f, t in replacements.items():
        s = s.replace(f, t)
    s = re.sub(r'[^a-z0-9-]', '-', s)
    s = re.sub(r'-+', '-', s)
    s = s.strip('-')
    return s

# Get current clinica-medica structure
cm = assuntos.get('clinica-medica', {})
current_subs = cm.get('subcategorias', {})
current_detalhes = cm.get('subdetalhes', {})

# Add the 4 specialties as subcategories
specialty_subcats = {
    slugify(nome): {"nome": nome, "total": len(SPECIALTY_QUESTIONS[slug])}
    for slug, nome in SPECIALTIES.items()
}

# Merge into existing subcategories (don't overwrite existing ones)
for slug, info in specialty_subcats.items():
    if slug not in current_subs:
        current_subs[slug] = info
    else:
        # Update count
        current_subs[slug]['total'] = info['total']

# Also update counts for existing subcategories
for sub_slug, sub_info in current_subs.items():
    nome = sub_info['nome']
    if nome in sub_counts:
        sub_info['total'] = sub_counts[nome]

cm['total'] = len(all_qs)
cm['subcategorias'] = current_subs

# Add subdetalhes entries for the new specialties
# Get taxonomy from hierarquia if available
for slug, nome in SPECIALTIES.items():
    sub_slug = slugify(nome)
    if sub_slug not in current_detalhes:
        # Look in hierarchy for subdetalhes
        h_info = hierarquia.get(slug, {})
        sub_detalhes_list = h_info.get('subdetalhes', h_info.get('subcategorias', []))
        if isinstance(sub_detalhes_list, dict):
            # It's already a dict (subdetalhes format)
            pass
        elif isinstance(sub_detalhes_list, list) and len(sub_detalhes_list) > 0:
            current_detalhes[sub_slug] = {
                "nome": nome,
                "subcategorias": sub_detalhes_list,
                "total_questoes": sub_counts.get(nome, 0)
            }
        else:
            # No subdetalhes for this specialty
            pass

cm['subdetalhes'] = current_detalhes

# Update clinica-medica in assuntos
assuntos['clinica-medica'] = cm

# Remove the 4 standalone areas from top level (but keep the slug in assuntos
# if it has data — actually we remove them entirely)
for slug in SPECIALTIES:
    if slug in assuntos:
        del assuntos[slug]
        print(f"  assuntos.json: removido '{slug}' do topo")

# Write updated assuntos.json
with open(os.path.join(DATA, 'assuntos.json'), 'w') as f:
    json.dump(assuntos, f, ensure_ascii=False, indent=2)
print(f"  assuntos.json: atualizado com {len(assuntos)} áreas")

# ─── 6. Summary ───
print(f"\n✅ Migração concluída!")
print(f"  Clínica Médica agora tem {len(all_qs)} questões em {len(current_subs)} subcategorias")
for sub_slug, sub_info in sorted(current_subs.items()):
    print(f"    - {sub_info['nome']}: {sub_info['total']} questões")

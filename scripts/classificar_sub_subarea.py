#!/usr/bin/env python3
"""
Auto-classifica sub_subarea (sub-subcategoria) para questões da Clínica Médica.
Baseia-se nos subdetalhes de assuntos.json e faz matching por keywords.
"""
import json, os, re
from collections import defaultdict

BASE = os.path.expanduser('~/hermesmed-questoes')
DATA = os.path.join(BASE, 'data')

# ─── 1. Load data ───
with open(os.path.join(DATA, 'assuntos.json')) as f:
    assuntos = json.load(f)

with open(os.path.join(DATA, 'clinica-medica.json')) as f:
    clinica = json.load(f)

subdetalhes = assuntos.get('clinica-medica', {}).get('subdetalhes', {})

# ─── 2. Build keyword maps for each sub_subarea ───
def gerar_keywords(nome):
    """Gera keywords a partir do nome da sub-subcategoria."""
    nome_clean = nome.lower().strip()
    nome_clean = re.sub(r'\([^)]*\)', '', nome_clean)  # remove parenteses
    nome_clean = re.sub(r'[^\w\s]', '', nome_clean)      # remove pontuação
    # Split into words, drop very short ones
    words = [w.strip() for w in nome_clean.split() if len(w.strip()) > 2]
    return words

SUB_SUB_KW = {}  # {subarea_slug: {sub_subarea_nome: [keywords]}}
for sub_slug, detalhes in subdetalhes.items():
    nome = detalhes.get('nome', '')
    subcats = detalhes.get('subcategorias', [])
    kw_map = {}
    for sc in subcats:
        words = gerar_keywords(sc)
        # Add the full nome as a phrase match too
        kw_map[sc] = {
            'phrase': sc.lower().strip(),
            'words': words,
            'short': sc.lower().replace('(', '').replace(')', '').strip()
        }
    SUB_SUB_KW[sub_slug] = kw_map

# ─── 3. Also build generic subarea name -> slug lookup ───
subarea_to_slug = {}
cm_subs = assuntos.get('clinica-medica', {}).get('subcategorias', {})
for sub_slug, sub_info in cm_subs.items():
    subarea_to_slug[sub_info['nome']] = sub_slug

# ─── 4. Classify each question ───
stats = defaultdict(lambda: defaultdict(int))
classified = 0
unclassified = 0

for q in clinica.get('questoes', []):
    subarea_nome = q.get('subarea', '')
    if not subarea_nome:
        continue
    
    sub_slug = subarea_to_slug.get(subarea_nome)
    if not sub_slug:
        continue
    
    kw_map = SUB_SUB_KW.get(sub_slug, {})
    if not kw_map:
        continue
    
    # Build text to search
    texto = f"{q.get('enunciado','')} {q.get('explicacao','')} {q.get('correta','')}".lower()
    texto += ' ' + ' '.join(str(v) for v in (q.get('alternativas') or {}).values()).lower()
    
    best_match = ''
    best_score = 0
    
    for sub_sub, info in kw_map.items():
        score = 0
        # Phrase match (full sub-subcategory name)
        if info['phrase'] in texto:
            score += 5
        # Short version
        if info['short'] in texto:
            score += 3
        # Individual word matches
        score += sum(1 for w in info['words'] if w in texto)
        
        if score > best_score:
            best_score = score
            best_match = sub_sub
    
    if best_match and best_score >= 2:
        q['sub_subarea'] = best_match
        classified += 1
        stats[sub_slug][best_match] += 1
    else:
        q['sub_subarea'] = ''
        unclassified += 1

# ─── 5. Save ───
with open(os.path.join(DATA, 'clinica-medica.json'), 'w') as f:
    json.dump(clinica, f, ensure_ascii=False, indent=2)

print(f"✅ Classificação concluída!")
print(f"  Classificadas: {classified}")
print(f"  Não classificadas: {unclassified}")
print()
for sub_slug, matches in sorted(stats.items()):
    sub_nome = subdetalhes.get(sub_slug, {}).get('nome', sub_slug)
    total = sum(matches.values())
    print(f"  {sub_nome}: {total} questões classificadas")
    for sub_sub, cnt in sorted(matches.items(), key=lambda x: -x[1]):
        print(f"    - {sub_sub}: {cnt}")

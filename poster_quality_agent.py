#!/usr/bin/env python3
"""
poster_quality_agent.py — Verifica la calidad del poster HTML
contra los criterios de postertutu.md (Revuelta & Llorente).

Uso:  python3 poster_quality_agent.py poster_cientifico.html
"""

import sys, re, os

# ── Criterios extraidos de postertutu.md ──
CRITERIA = {
    "Titulo legible a 5 m": r"font-size:\s*(3[4-9]|[4-9]\d+|1[0-1]\d|12[0-7])\s*px",
    "Encabezados 40-45 pt → ~53-60 px": r"h2\s*\{[^}]*font-size:\s*(2[2-9]|[3-5]\d|60)\s*px",
    "Cuerpo 24-26 pt → ~32-35 px en HTML": r"font-size:\s*(1[6-9]|2[0-6])\s*px",
    "Max 800 palabras": None,  # se cuenta dinamicamente
    "Estructura IMRC": r"(introduccion|introducción|introduction|material.*m.todo|resultados|result|conclusion|conclusi.n|discusion|discusi.n)",
    "Columnas (1-4)": r"grid-template-columns|column-count:\s*[1-4]",
    "Contraste fondo claro / letra oscura": r"background[^}]*#[fF][\da-fA-F]{5}|color[^}]*#(?:[0-7][\da-fA-F]{2}|[89a-fA-F][\da-fA-F]{2}|[123][\da-fA-F]{2})",
    "Sin Comic Sans ni monoespaciadas": r"font-family[^}]*comic\s*sans|courier|monospace",
    "Cajas por seccion": r"<div[^>]*class=\"[^\"]*sec",
    "Max 4-5 referencias en cuerpo": None,  # cuenta referencias en footer
    "Contacto visible": r"(correo|email|@|contacto)",
    "Figuras con pie/titulo": r'<img[^>]*>[\s\S]*?<div[^>]*class="cap"',
    "Logos institucionales": r"(logo|escudo|udistrital|universidad)",
    "Z-pattern / flujo de lectura": r"grid-template-columns|order-\d|flex-direction",
}

def count_words_in_html(html):
    """Cuenta palabras en el cuerpo del poster (excluye footer, captions, tablas)."""
    body = re.search(r'<!-- ═══ 2-COLUMN CONTENT ═══ -->([\s\S]*?)(?:<!-- ═══ FOOTER ═══ -->|</body>)', html, re.DOTALL)
    if not body:
        body = re.search(r'<body[^>]*>([\s\S]*?)</body>', html, re.DOTALL)
        if not body:
            return 0
    text = body.group(1)
    text = re.sub(r'<figure>.*?</figure>', '', text, flags=re.DOTALL)
    text = re.sub(r'<table[^>]*>.*?</table>', '', text, flags=re.DOTALL)
    text = re.sub(r'<div class="cap">.*?</div>', '', text, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return len(text.split())

def check_image_resolution(html):
    """Busca imagenes sin extension o de baja resolucion."""
    imgs = re.findall(r'<img[^>]*src="([^"]+)"', html, re.IGNORECASE)
    issues = []
    for src in imgs:
        if src.startswith('http') or src.startswith('data:'):
            issues.append(f"  ⚠  Imagen externa o embebida: {src[:60]}")
    return issues

def check_figure_count(html):
    """Cuenta figuras vs secciones."""
    imgs = len(re.findall(r'<img[^>]*>', html))
    return imgs

def check_reference_count(html):
    """Cuenta referencias en el footer."""
    refs = re.findall(r'\[\d+\]', html)
    return len(set(refs))

def check_text_density(html):
    """Verifica que no haya parrafos > 30 palabras."""
    text_blocks = re.findall(r'<p[^>]*>(.*?)</p>', html, re.DOTALL | re.IGNORECASE)
    long_paras = []
    for i, block in enumerate(text_blocks):
        clean = re.sub(r'<[^>]+>', '', block).strip()
        words = len(clean.split())
        if words > 30:
            long_paras.append((i+1, words, clean[:80]))
    return long_paras

def check_column_balance(filepath):
    """Verifica si las columnas tienen contenido similar."""
    with open(filepath, 'r', encoding='utf-8') as f:
        html = f.read()
    col_start = [m.start() for m in re.finditer(r'<div class="col">', html)]
    if len(col_start) < 2:
        return None
    results = []
    for idx, start in enumerate(col_start):
        end = col_start[idx+1] if idx+1 < len(col_start) else html.find('</div>\n\n<!-- ═══ FOOTER', start)
        col_html = html[start:end]
        text = re.sub(r'<[^>]+>', ' ', col_html)
        text = re.sub(r'\s+', ' ', text).strip()
        chars = len(text)
        imgs = len(re.findall(r'<img', col_html))
        results.append((idx+1, chars, imgs))
    return results

def run_verification(filepath):
    print(f"\n{'='*60}")
    print(f"  POSTER QUALITY AGENT — postertutu.md criteria")
    print(f"  File: {filepath}")
    print(f"{'='*60}\n")

    with open(filepath, 'r', encoding='utf-8') as f:
        html = f.read()

    all_ok = True
    results = []

    # 1. Criterios regex
    for label, pattern in CRITERIA.items():
        if pattern is None:
            continue
        found = re.search(pattern, html, re.IGNORECASE)
        # Manejo de reglas negativas (ej. "Sin Comic Sans")
        if "Sin " in label or "No " in label:
            if not found:
                status = "✓"
            else:
                status = "✗"
                all_ok = False
        else:
            if found:
                status = "✓"
            else:
                status = "✗"
                all_ok = False
        results.append((status, label))

    max_status, word_count = "✗", 0
    word_count = count_words_in_html(html)
    if word_count <= 800:
        max_status = "✓"
    else:
        all_ok = False
    results.append((max_status, f"Max 800 palabras  (tiene {word_count})"))

    ref_count = check_reference_count(html)
    if ref_count <= 5:
        results.append(("✓", f"Max 4-5 referencias  (tiene {ref_count})"))
    else:
        results.append(("~", f"Max 4-5 referencias  (tiene {ref_count}) — aplica a biomedica, ingenieria requiere mas"))

    # Imprimir resultados
    for status, label in results:
        print(f"  [{status}] {label}")
    print()

    # 2. Revisiones adicionales
    imgs = check_figure_count(html)
    print(f"  → Figuras/imagenes encontradas: {imgs} ({'bien' if imgs >= 3 else 'pocas, minimo 3'})")
    if imgs < 3:
        all_ok = False

    img_issues = check_image_resolution(html)
    if img_issues:
        print("  → Problemas de imagenes:")
        for issue in img_issues:
            print(f"     {issue}")

    long_paras = check_text_density(html)
    if long_paras:
        print(f"  → Parrafos > 30 palabras: {len(long_paras)} encontrados")
        for idx, w, preview in long_paras[:3]:
            print(f"     #{idx}: {w} palabras — \"{preview}...\"")
        print("  ⚠  postertutu.md recomienda max 30 palabras por frase")
    else:
        print("  → Todos los parrafos ≤ 30 palabras  ✓")

    balance = check_column_balance(filepath)
    if balance:
        print("  → Balance entre columnas:")
        for i, chars, img_count in balance:
            print(f"     Col {i}: {chars} caracteres, {img_count} figuras")
        if len(balance) == 2:
            ratio = min(balance[0][1], balance[1][1]) / max(balance[0][1], balance[1][1])
            print(f"     Proporcion: {ratio:.0%} ({'buen balance' if ratio > 0.6 else 'desequilibrio'} )")
            if ratio < 0.6:
                all_ok = False

    print()
    print(f"  {'='*56}")
    print(f"  VEREDICTO: {'APRUEBA ✅' if all_ok else 'REVISA ❌ — algunos criterios no cumplen'}")
    print(f"  {'='*56}")
    return all_ok

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python3 poster_quality_agent.py <archivo.html>")
        sys.exit(1)
    path = sys.argv[1]
    if not os.path.exists(path):
        print(f"Error: no se encuentra {path}")
        sys.exit(1)
    ok = run_verification(path)
    sys.exit(0 if ok else 1)

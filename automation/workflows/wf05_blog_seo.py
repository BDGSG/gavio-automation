"""WF05 — Blog SEO Agent.

Cron : Lun/Mer/Ven 06h Paris.
Pipeline complet :
  1. Selection topic (5 piliers ponderes : test, comparatif, guide, niche, lifestyle)
  2. Generation article (Claude Sonnet 4.5, ~1800 mots, structure SEO)
  3. Generation image hero (FLUX via Kie.ai, 1200x630)
  4. Upload image -> WP media
  5. Publication article -> WP /wp-json/wp/v2/posts
  6. Notif Telegram

Stockage des sujets deja traites pour eviter les doublons.
"""
import json
import logging
import random
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

from automation.config import Config
from automation.utils.error_handling import workflow_handler
from automation.workflows import get_claude, get_wc, get_telegram

log = logging.getLogger("automation.wf05")
PARIS = ZoneInfo("Europe/Paris")

PILIERS = ["test", "comparatif", "guide", "niche", "lifestyle"]
PILIER_WEIGHTS = {
    "test": 0.20,        # Test produit
    "comparatif": 0.20,  # Comparatif / vs / top
    "guide": 0.25,       # Guide d'achat / tutoriel
    "niche": 0.15,       # Sujets pointus tech
    "lifestyle": 0.20,   # Lifestyle hi-tech
}

PILIER_DESCRIPTIONS = {
    "test": (
        "Test produit detaille : une paire de lunettes (soleil ou vue) d'une marque "
        "specifique du catalogue Gavio, prise en main, qualites, defauts, verdict. "
        "Exemples : 'Test des lunettes de soleil Nike Windtrack : un mois au quotidien', "
        "'Test Skechers SE00058 : legerete et confort a l'epreuve'."
    ),
    "comparatif": (
        "Comparatif / Versus / Top : classement, comparaison de plusieurs modeles "
        "ou marques de lunettes. Exemples : 'Ray-Ban vs Nike : quelles lunettes de "
        "soleil choisir en 2026', 'Top 5 montures de vue legeres pour porter toute "
        "la journee', 'Verres polarises vs verres teintes classiques'."
    ),
    "guide": (
        "Guide d'achat ou tutoriel pratique : comment choisir sa monture, "
        "comment entretenir ses lunettes. Exemples : 'Comment choisir sa forme de "
        "monture selon son visage', 'Guide complet des indices de protection UV "
        "pour lunettes de soleil', 'Lunettes de vue : verres fins vs verres "
        "amincis, que choisir ?'."
    ),
    "niche": (
        "Sujet niche optique pointu : technologies de verres, deep dives. "
        "Exemples : 'Verres polarises : comment ca marche vraiment ?', "
        "'Traitement anti-lumiere bleue : utile ou marketing ?', "
        "'Lunettes de sport : pourquoi une monture technique change tout'."
    ),
    "lifestyle": (
        "Lifestyle autour des lunettes : usages au quotidien, style, tendances. "
        "Exemples : '5 lunettes de soleil tendance pour cet ete', "
        "'Comment associer ses lunettes a son style vestimentaire', "
        "'Lunettes de vue et teletravail : proteger ses yeux des ecrans'."
    ),
}

PRIORITY_KEYWORDS = [
    "lunettes de soleil", "lunettes de vue", "lunettes homme", "lunettes femme",
    "monture optique", "verres polarises", "lunettes de soleil pas cher",
    "lunettes de vue tendance", "protection uv lunettes", "lunettes de sport",
]

# Stockage local des sujets traites (pour eviter les doublons)
TOPICS_HISTORY_FILE = Path("/data/gavio_blog/topics_done.json")


def _load_history() -> list:
    try:
        if TOPICS_HISTORY_FILE.exists():
            return json.loads(TOPICS_HISTORY_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        log.warning("Cannot load topics history: %s", e)
    return []


def _save_history(history: list):
    try:
        TOPICS_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        TOPICS_HISTORY_FILE.write_text(
            json.dumps(history[-200:], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as e:
        log.warning("Cannot save topics history: %s", e)


def _pick_pilier() -> str:
    r = random.random()
    cum = 0.0
    for pilier, weight in PILIER_WEIGHTS.items():
        cum += weight
        if r <= cum:
            return pilier
    return PILIERS[0]


def _generate_topic(pilier: str, history: list) -> dict:
    """Demande a Claude de proposer un sujet pour ce pilier."""
    claude = get_claude()
    if not claude:
        raise RuntimeError("Claude non configure (ANTHROPIC_API_KEY manquant)")

    history_text = "\n".join(f"- {h.get('title', '')}" for h in history[-30:])
    keywords_text = ", ".join(random.sample(PRIORITY_KEYWORDS, k=5))

    system = (
        "Tu es expert SEO et editor en chef du blog de Gavio, une boutique "
        "francaise de lunettes (soleil et vue). Tu proposes UN seul sujet "
        "d'article precis, percutant, oriente search intent FR. "
        "Public : acheteurs de lunettes, 20-50 ans, France."
    )
    user = f"""Pilier : {pilier}
Description : {PILIER_DESCRIPTIONS[pilier]}

Sujets DEJA traites (ne pas dupliquer) :
{history_text or 'Aucun (premier article)'}

Mots-cles prioritaires a viser : {keywords_text}

Renvoie UNIQUEMENT un JSON :
{{
  "title": "titre H1 percutant 50-65 caracteres",
  "slug": "slug-url-concis",
  "meta_description": "meta 145-160 caracteres",
  "primary_keyword": "mot-cle principal",
  "secondary_keywords": ["3", "ou", "4"],
  "outline": ["Section 1 H2", "Section 2 H2", "..."],
  "angle": "angle editorial unique en 1 phrase"
}}
"""
    raw = claude.generate(system, user, max_tokens=1200, temperature=0.9)
    # Extract JSON
    match = re.search(r"\{[\s\S]+\}", raw)
    if not match:
        raise RuntimeError(f"Pas de JSON dans la reponse Claude : {raw[:200]}")
    return json.loads(match.group(0))


def _generate_article(topic: dict, pilier: str) -> str:
    """Genere l'article HTML complet (~1800 mots)."""
    claude = get_claude()
    system = (
        "Tu es un journaliste francais expert SEO specialise optique/lunetterie. "
        "Tu ecris des articles approfondis, factuels, sans bullshit. Style direct, "
        "premium mais accessible. Tu integres naturellement les mots-cles SEO."
    )
    user = f"""Ecris l'article complet en HTML semantique.

TITRE : {topic['title']}
ANGLE : {topic.get('angle', '')}
MOT-CLE PRINCIPAL : {topic['primary_keyword']}
MOTS-CLES SECONDAIRES : {", ".join(topic.get('secondary_keywords', []))}
PILIER : {pilier}
PLAN PROPOSE : {", ".join(topic.get('outline', []))}

CONTRAINTES :
- 1500 a 2000 mots
- HTML : <h2>, <h3>, <p>, <ul>, <li>, <strong>
- Pas de <h1> (le titre est gere par WP)
- Intro punchy (3-4 phrases) qui hook + promet
- Au moins 4 sections H2 avec H3 si pertinent
- Une FAQ a la fin (3-5 questions, format <h2>FAQ</h2> + <h3>Question</h3><p>Reponse</p>)
- Conclusion bref avec CTA vers la categorie produit Gavio (lien vers https://gavio.fr)
- TON : direct, informe, premium-tech (pas de cliches commerciaux, pas d'hyperboles vides)
- N'invente JAMAIS de specs techniques precises non verifiables
- Renvoie UNIQUEMENT le HTML (pas de markdown, pas de bloc code)
"""
    return claude.generate(system, user, max_tokens=6000, temperature=0.7)


def _generate_hero_image(topic: dict) -> bytes | None:
    """Genere l'image hero via Kie.ai FLUX. Retourne bytes JPEG."""
    if not Config.KIE_API_KEY:
        log.warning("KIE_API_KEY absent, skip hero image")
        return None
    try:
        prompt = (
            f"editorial eyewear magazine cover, ultra premium glasses product "
            f"photography, clean minimalist composition, {topic['primary_keyword']}, "
            f"soft studio lighting, dark gradient background, 16:9, no text, "
            f"shot on Hasselblad, photorealistic"
        )
        # API Kie.ai FLUX (endpoint generique)
        r = requests.post(
            "https://api.kie.ai/api/v1/images/generate",
            headers={"Authorization": f"Bearer {Config.KIE_API_KEY}"},
            json={
                "model": "flux-pro",
                "prompt": prompt,
                "width": 1200,
                "height": 630,
            },
            timeout=120,
        )
        r.raise_for_status()
        data = r.json()
        url = (
            data.get("data", {}).get("url")
            or data.get("imageUrl")
            or (data.get("images") or [None])[0]
        )
        if not url:
            log.warning("Pas d'URL image dans la reponse Kie.ai : %s", data)
            return None
        img = requests.get(url, timeout=60)
        img.raise_for_status()
        return img.content
    except Exception as e:
        log.error("Hero image generation failed: %s", e)
        return None


@workflow_handler("wf05_blog_seo")
def run():
    wc = get_wc()
    tg = get_telegram()
    claude = get_claude()

    if not claude:
        log.error("Claude non disponible")
        return {"status": "error", "reason": "no_claude"}

    history = _load_history()
    pilier = _pick_pilier()
    log.info("Pilier choisi : %s", pilier)

    topic = _generate_topic(pilier, history)
    log.info("Topic : %s", topic.get("title"))

    article_html = _generate_article(topic, pilier)
    log.info("Article genere : %d chars", len(article_html))

    # Image hero
    media_id = None
    image_bytes = _generate_hero_image(topic)
    if image_bytes:
        try:
            filename = f"{topic['slug']}-hero.jpg"
            media = wc.upload_media(image_bytes, filename, mime="image/jpeg")
            media_id = media.get("id")
            log.info("Hero image upload : media_id=%s", media_id)
        except Exception as e:
            log.warning("Upload media failed: %s", e)

    # Publication WP
    try:
        post = wc.create_post(
            title=topic["title"],
            content=article_html,
            excerpt=topic.get("meta_description", ""),
            status="publish",
            slug=topic.get("slug"),
            featured_media=media_id,
        )
        url = post.get("link", f"{Config.WC_URL}/?p={post.get('id', '?')}")
    except Exception as e:
        log.error("WP publish failed: %s", e)
        tg.send_message(f"❌ Blog SEO : echec publication\n{e}")
        return {"status": "error"}

    # Save history
    history.append({
        "title": topic["title"],
        "pilier": pilier,
        "date": datetime.now(tz=PARIS).isoformat(),
        "url": url,
    })
    _save_history(history)

    tg.send_message(
        f"✍️ *Nouvel article Gavio publie*\n\n"
        f"\U0001f4dd {topic['title']}\n"
        f"\U0001f3f7️ Pilier : {pilier}\n"
        f"\U0001f517 {url}"
    )
    return {"status": "ok", "url": url, "title": topic["title"]}

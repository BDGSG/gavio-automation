# Gavio Automation

Microservice Python (FastAPI/Flask + APScheduler) qui orchestre les workflows
e-commerce de [gavio.fr](https://gavio.fr).

Adapte des workflows SensationToys (n8n -> Python) pour l'environnement Gavio :
- **WooCommerce** au lieu d'un autre stack
- **CJ Dropshipping** au lieu de Dreamlove
- **Resend** pour l'email transactionnel
- **Stripe** pour le paiement / remboursement
- Branding Apple-like Gavio

## Structure

```
automation/
├── main.py                  # Entry point (Flask + APScheduler)
├── config.py                # Lecture env vars
├── requirements.txt
├── Dockerfile
├── .env.example
├── clients/
│   ├── cj_dropshipping.py   # API CJ (auth, products, stock, orders, tracking)
│   ├── woocommerce.py       # WC REST + WP REST (orders, products, posts, media)
│   ├── telegram.py          # Bot Gavio
│   ├── resend.py            # Emails transactionnels FR (template Apple-like)
│   ├── claude.py            # Claude Sonnet 4.5 (avec fallback Kie.ai)
│   └── brevo.py             # Email marketing (sequences + newsletter)
├── workflows/
│   ├── wf01_commande_auto.py     [COMPLET] webhook → anti-fraude → notif
│   ├── wf02_tracking_auto.py     [COMPLET] cron 4h → CJ tracking → maj WC
│   ├── wf03_remboursement.py     [COMPLET] webhook → boutons Telegram
│   ├── wf04_daily_report.py      [COMPLET] cron 20h → resume jour Telegram
│   ├── wf05_blog_seo.py          [COMPLET] Lun/Mer/Ven 6h → article + image
│   ├── wf06_sync_stock_cj.py     [COMPLET] cron 4h → CJ stock → WC batch
│   ├── wf07_transmission_cj.py   [COMPLET] cron 15min → cree commande CJ
│   ├── wf12_monitoring.py        [COMPLET] cron 5min → CPU/RAM/disk
│   ├── wf22_wp_maintenance.py    [COMPLET] Dim 4h → updates plugins/core SSH
│   ├── wf08_nouveaux_produits.py [SQUELETTE] veille catalogue CJ
│   ├── wf10_meta_social.py       [SQUELETTE] FB + IG
│   ├── wf11_tiktok.py            [SQUELETTE] TikTok via Ayrshare
│   ├── wf13_faq_enrichment.py    [SQUELETTE] FAQ produits via Claude
│   ├── wf14_brevo_emails.py      [SQUELETTE] sequences welcome / cart / post-achat
│   ├── wf15_newsletter.py        [SQUELETTE] newsletter mensuelle
│   ├── wf17_seo_monitoring.py    [SQUELETTE] tracking positions Google
│   ├── wf18_concurrence.py       [SQUELETTE] veille Amazon / Fnac / Boulanger
│   └── wf21_google_shopping.py   [SQUELETTE] feed XML pour GMC
├── web/
│   ├── app.py                    # Flask : webhooks + decision callbacks
│   ├── decision_store.py         # Store en memoire pour boutons Telegram
│   └── routes/                   # (stubs pour separation future)
└── utils/
    ├── error_handling.py         # Decorateur @workflow_handler
    └── logging.py                # Setup stdout + fichier
```

## Workflows actifs

| WF | Nom | Schedule | Statut |
|----|-----|----------|--------|
| WF01 | Commande Auto | Webhook | COMPLET |
| WF02 | Tracking Auto CJ | Cron 4h | COMPLET |
| WF03 | Remboursement | Webhook | COMPLET (Stripe TODO) |
| WF04 | Rapport quotidien | 20h Paris | COMPLET |
| WF05 | Blog SEO | Lun/Mer/Ven 6h | COMPLET |
| WF06 | Sync Stock CJ | Cron 4h | COMPLET |
| WF07 | Transmission CJ | Cron 15min | COMPLET |
| WF08 | Nouveaux produits CJ | Dim 10h | SQUELETTE |
| WF10 | Meta FB+IG | 12h | SQUELETTE |
| WF11 | TikTok | 13h + 20h | SQUELETTE |
| WF12 | Monitoring VPS | Cron 5min | COMPLET |
| WF13 | FAQ enrichment | Dim 11h | SQUELETTE |
| WF14 | Brevo emails | 10h | SQUELETTE |
| WF15 | Newsletter mois | 1er du mois 10h30 | SQUELETTE |
| WF17 | SEO monitoring | Dim 8h | SQUELETTE |
| WF18 | Veille concurrence | Lun 7h | SQUELETTE |
| WF21 | Google Shopping | 5h quotidien | SQUELETTE |
| WF22 | WP Maintenance | Dim 4h | COMPLET |

> Workflows EXCLUS (specifiques SensationToys) : WF09 X/Twitter, WF09b Threads,
> WF16 Bluesky, WF19 Eva Laurent influencer.

## Setup local

```bash
cd automation
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/Mac
pip install -r requirements.txt

cp .env.example ../.env         # le .env doit etre A LA RACINE de gavio-multiproduct/
# editer .env avec les valeurs reelles

# lancer (depuis gavio-multiproduct/)
python -m automation
```

Le serveur webhook ecoute sur `:5000`.
Health check : `curl http://localhost:5000/health` -> `{"status":"ok"}`.

## Tester un workflow individuellement

```python
# Depuis gavio-multiproduct/, lancer un shell Python :
python -c "
from automation.utils.logging import setup_logging
from automation.workflows import init_clients
from automation.workflows import wf04_daily_report

setup_logging()
init_clients()
wf04_daily_report.run()
"
```

Remplacer `wf04_daily_report` par n'importe quel autre :
`wf02_tracking_auto`, `wf06_sync_stock_cj`, `wf07_transmission_cj`,
`wf12_monitoring`, etc.

Pour tester un webhook (WF01) en local :
```bash
curl -X POST http://localhost:5000/webhook/woocommerce/order \
  -H "Content-Type: application/json" \
  -d @test_order.json
```

## Variables d'environnement requises

Voir `.env.example` pour la liste complete. Les valeurs critiques :

**Indispensables pour faire tourner les WF critiques :**
- `WC_URL`, `WC_KEY`, `WC_SECRET` — REST API WooCommerce (a configurer une fois
  le site en ligne)
- `CJ_API_KEY` — deja fournie (CJ3934481@api@...)
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` — bot Gavio (deja prets)
- `RESEND_API_KEY` — emails transactionnels (deja fournie)
- `ANTHROPIC_API_KEY` — pour blog SEO (recuperer depuis Coolify shared vars)

**Optionnels (pour activer les workflows squelettes) :**
- `BREVO_API_KEY` — sequences email + newsletter (a fournir par utilisateur)
- `META_PAGE_ACCESS_TOKEN` — FB + IG
- `AYRSHARE_API_KEY` ou `TIKTOK_ACCESS_TOKEN` — TikTok
- `DATAFORSEO_LOGIN` / `_PASSWORD` — SEO tracking
- `SSH_HOST` / `SSH_USER` / `SSH_PASS` / `WP_PATH` — pour WF22 maintenance

## Deploiement Coolify

L'app Gavio est deja deployee sur Coolify (UUID `kw8404kgscck4g40ockogkwc`,
projet `l48kcwssk8gsg4gsksosocc8`).

Pour ajouter le service automation :

1. Creer une nouvelle app dans le projet Gavio :
   - Source : meme repo GitHub `BDGSG/gavio` (branche `main`)
   - Build pack : `dockerfile`
   - Dockerfile path : `automation/Dockerfile`
   - Port expose : `5000`
   - Custom domain (optionnel) : `automation.gavio.fr`

2. Ajouter les env vars dans Coolify (UI > Environment Variables) :
   ```
   WC_URL=https://gavio.fr
   WC_KEY=ck_xxx
   WC_SECRET=cs_xxx
   CJ_API_KEY=CJ3934481@api@dc4b7fab646f4e6c9876d2486266f4bf
   TELEGRAM_BOT_TOKEN=8546540157:AAFBkRmkKU45clBLt9O6HB0jNMHRCfLpAPo
   TELEGRAM_CHAT_ID=7445971784
   RESEND_API_KEY=re_RXcHaNcA_PyE37EPqE1nYK8deVmxs6ktu
   ANTHROPIC_API_KEY=sk-ant-...
   KIE_API_KEY=2c44ed8970990c113f4dcf4742018516
   WEBHOOK_BASE_URL=https://<URL-coolify-automation>
   TZ=Europe/Paris
   ```

3. Volume persistant : `/data` -> `/data` (pour blog topics history,
   donnees scrapes, logs)

4. Deploy

5. Configurer le webhook WooCommerce :
   - WP Admin > WooCommerce > Settings > Advanced > Webhooks > Add
   - Topic : `Order created`
   - Delivery URL : `https://<URL-automation>/webhook/woocommerce/order`
   - Status : Active

## Conventions

- **Tous les workflows** suivent le pattern :
  ```python
  @workflow_handler("wfXX_name")
  def run():
      log.info("WFXX start")
      # ...
      log.info("WFXX done")
      return {"status": "ok", ...}
  ```
- **Erreurs** : capturees automatiquement par `@workflow_handler` et envoyees
  vers Telegram (chat_id par defaut).
- **Clients API** : init unique au demarrage via `init_clients()`, accedes
  via `get_cj()`, `get_wc()`, `get_telegram()`, etc.
- **Meta WC critiques** :
  - `_cj_vid` (sur le PRODUIT) : variant ID CJ — necessaire pour stock + commande
  - `_cj_pid` (sur le PRODUIT) : product ID CJ
  - `_cj_order_id` (sur la COMMANDE) : ID commande CJ apres transmission
  - `_cj_submitted_at` (sur la COMMANDE) : timestamp ISO transmission
  - `_tracking_number` (sur la COMMANDE) : numero suivi
  - `_tracking_url` (sur la COMMANDE) : URL suivi 17track / transporteur

## Roadmap

1. Configurer les API keys WooCommerce une fois Gavio en ligne
2. Creer les 20 produits dans WC avec meta `_cj_vid` et `_cj_pid`
3. Tester WF01 (webhook commande) avec une commande test
4. Tester WF07 (transmission CJ) en mode manuel apres une commande test
5. Activer le scheduler en prod (deploiement Coolify)
6. Implementer les workflows squelettes selon priorite business
   (recommande : WF14 Brevo emails > WF10 Meta social > WF21 Google Shopping)

## Differences principales vs SensationToys

| Element | SensationToys | Gavio |
|---------|--------------|-------|
| Fournisseur | Dreamlove (scraping web) | CJ Dropshipping (API officielle) |
| Auth fournisseur | Cookies session login | API key persistante |
| Stock sync | Scrape paginated | API JSON queryByVid |
| Commandes | Scraping form panier | API createOrder JSON |
| Tracking | Scrape "Mes commandes" | API trackInfo |
| Email transactionnel | Brevo | Resend (templates Apple-like) |
| Paiement | Mollie | Stripe + PayPal |
| Branding messages | SexShop FR | Hi-tech premium FR |
| Catalogue | 3173 produits adultes | 20 produits hi-tech curates |
| Pillars blog | bien-etre/couple/etc | test/comparatif/guide/niche/lifestyle |

## Auteur

Genere a partir des workflows n8n + automation Python SensationToys
adaptee pour Gavio le 27/04/2026.

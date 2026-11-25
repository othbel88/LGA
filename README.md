# ⚠️ Branche de prévisualisation — ne pas fusionner

Cette branche (`preview-recette-v6`) contient une **version de travail non indexable** du
nouveau site du Grand Alcazar, destinée uniquement à une prévisualisation distincte du
site actuellement en ligne (GitHub Pages, branche `main`).

- Générée automatiquement à partir de `redesign-grand-alcazar-v2` (commit `fe3bdb3`)
- Toutes les pages portent une balise `<meta name="robots" content="noindex, nofollow, noarchive">`
- `robots.txt` bloque totalement l'indexation (`Disallow: /`)
- Aucun `sitemap.xml` n'est généré
- Un bandeau visuel « APERÇU DE TRAVAIL » rappelle sur chaque page qu'il ne s'agit pas
  de la version en ligne

**Ne jamais fusionner cette branche dans `main` ni dans `redesign-grand-alcazar-v2`.**
Elle sera supprimée une fois la prévisualisation terminée.

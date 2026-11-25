# tools/

Outils et sources de build non versionnés ailleurs (`/home/claude/build` et `/home/claude/src`
ne sont pas des dépôts Git — voir `TECHNICAL-ARCHITECTURE.md`). Conservés ici pour survivre aux
réinitialisations de session : un environnement de travail vierge ne contient **que** ce dépôt
Git ; tout ce qui n'y est pas commité est perdu.

## prev.py

Réécrit les chemins absolus (`href="/css/..."`, `src="/assets/..."`, etc.) d'un build normal
pour qu'il fonctionne sous un sous-chemin (GitHub Pages `/LGA/`, ou aperçu raw.githack
`othbel88/LGA/<branche>/`). Usage :

    python3 prev.py <build_normal> <build_prefixe> othbel88/LGA/<branche>

**Correctif du 25/11/2026 (dernières corrections v8)** : la version précédente de ce script
supprimait par erreur le `/` initial lors de la réécriture (`href="/css/x"` devenait
`href="othbel88/LGA/v8/css/x"` au lieu de `href="/othbel88/LGA/v8/css/x"`), transformant un
chemin voulu absolu en chemin relatif à la page courante. Résultat : CSS/JS/images cassés sur
toutes les pages situées à plus d'un niveau de profondeur (donc la quasi-totalité du site) —
confirmé à la fois en local et sur l'aperçu public raw.githack déjà poussé. Toujours utiliser
CETTE copie (`tools/prev.py`), jamais une copie de `/home/claude/prev.py` recréée de mémoire
dans une session future, pour éviter de réintroduire ce bug.

## build-sources/ — sauvegarde complète pour reconstruction depuis un environnement vierge

**Mise à jour du 25/11/2026 (fin de la phase de développement v8, tag `v8-design-validated`).**
Contient tout ce qu'une session future doit restaurer AVANT de lancer un premier build dans un
environnement neuf — sans ces fichiers, `build.py` ne peut pas s'exécuter (il lit `src/` comme
entrée et plusieurs fichiers de `build/` comme dépendances directes).

```
tools/build-sources/
├── requirements.txt       # dépendances Python (voir ci-dessous)
├── build/                 # = contenu nécessaire de /home/claude/build
│   ├── build.py           # générateur principal
│   ├── rooms_data.py      # données des 14 chambres (9 langues)
│   ├── respimg.py         # génération d'images responsives (bandeaux, vignettes)
│   ├── main.js            # JS réel du site (PAS le décoy de src/js/, voir piège ci-dessous)
│   ├── style.css          # CSS réel du site (PAS le décoy de src/css/, idem)
│   ├── poster.jpg         # image poster de la vidéo de visite
│   ├── img/                # petits assets additionnels copiés tels quels par build.py
│   ├── data/
│   │   └── legacy_histoire_room_pics.json
│   └── rooms/              # photos sources des 14 chambres (1.jpg, 2.jpg… par chambre)
└── src/                    # = copie complète de /home/claude/src (entrée du build, 9 langues)
    ├── api/                 # contact.php, subscribe.php, guard.php — aucun secret (PHP mail()
    │                        # natif, pas d'identifiants SMTP/API ; vérifié avant sauvegarde)
    ├── assets/              # médias (photos hors chambres, drapeaux, vidéo de visite)
    ├── ar/ de/ en/ es/ it/ ko/ ru/ zh/   # pages sources traduites, une arborescence par langue
    ├── book-online/ contact/ notre-histoire/ restaurant/ services/
    │   suites-chambres-1/ commentaires-et-distinctions/ compte/   # pages sources FR (= langue
    │                        # par défaut, à la racine, sans préfixe de langue)
    ├── embeds/              # badges tiers (Tripadvisor, Responsible Golf…)
    ├── css/ js/             # js/ est réel (gallery.js, booking.js, account.js, slides.json) ;
    │                        # css/style.css et js/main.js sont des DÉCOYS, voir piège ci-dessous
    ├── private/, robots.txt, sitemap.xml, .htaccess, index.html
```

**Non inclus, volontairement** :
- `build/_bandcache/` — cache d'images dérivées, régénéré automatiquement au premier build
  (voir le docstring de `respimg.py`) ; aucune perte si absent.
- `build/__pycache__/` — bytecode Python compilé, régénéré automatiquement.
- `build/hw.py`, `hw2.py`, `ov.py`, `shot.py`, `rooms_code.txt` — scripts de travail ponctuels,
  non importés par `build.py` ni par `respimg.py` (vérifié par recherche textuelle) : ne font
  pas partie de la chaîne de build, pas nécessaires à une reconstruction.
- Aucune donnée de formulaire (pas de `subscribers.csv` ni de fichier de limitation de débit
  `api/.rl/*` au-delà du `.htaccess` de protection) — rien de tel n'existait dans l'environnement
  au moment de la sauvegarde.

### Procédure de reconstruction depuis un environnement vierge

1. Cloner ce dépôt (branche `redesign-grand-alcazar-v2`, ou le tag `v8-design-validated` pour
   repartir exactement de l'état validé le 25/11/2026).
2. Restaurer l'arborescence de travail (hors du dépôt Git, par exemple sous `/home/claude`) :

       mkdir -p /home/claude/build /home/claude/src
       cp -r tools/build-sources/build/. /home/claude/build/
       cp -r tools/build-sources/src/.   /home/claude/src/

3. Installer les dépendances Python (`requirements.txt` ci-dessus) :

       pip install -r tools/build-sources/requirements.txt --break-system-packages

   Testé avec Python 3.13, beautifulsoup4 4.15.0, Pillow 12.3.0.
4. Lancer un build de production (pour OVH) :

       cd /home/claude/build
       python3 build.py /home/claude/src /home/claude/prod_build

   — ou un build de prévisualisation (bannière non-indexation, pas de sitemap) :

       LGA_PREVIEW=1 python3 build.py /home/claude/src /home/claude/prod_build

   **Attention** : `build.py` exécute `shutil.rmtree(OUT)` sur son 2ᵉ argument — ne jamais passer
   `/home/claude/lga` (ce dépôt) directement comme destination.
5. Pour publier un aperçu raw.githack sous un sous-chemin (jamais pour la mise en ligne OVH
   finale, qui sert depuis la racine du domaine) :

       python3 tools/prev.py /home/claude/prod_build /home/claude/prev_build othbel88/LGA/<branche>

6. Copier le résultat (`prod_build` pour OVH, ou `prev_build` pour un aperçu) dans une copie de
   travail de ce dépôt, sur la bonne branche, puis `git add -A && git commit && git push` —
   jamais directement sur `main` sans décision explicite d'Othmane (voir `DECISIONS.md`).

**Piège connu** : `src/css/style.css` et `src/js/main.js` sont des fichiers DÉCOYS, obsolètes et
non utilisés par le build réel — ne jamais les éditer ni les confondre avec `build/style.css` et
`build/main.js` ci-dessus. Le build réel copie toujours `style.css` et `main.js` depuis
`/home/claude/build`, jamais depuis `/home/claude/src/css` ou `/home/claude/src/js` pour ces deux
fichiers précis (confirmé par lecture directe de `build.py` : `shutil.copy2(os.path.join(BUILD,
'style.css'), ...)` / `os.path.join(BUILD, 'main.js')`, exécuté APRÈS la copie en bloc de
`src/js/` — qui, elle, fournit bien `gallery.js`, `booking.js`, `account.js` et `slides.json`,
ceux-là réels).

Après toute modification future de l'un des fichiers de `build/` (dans `/home/claude/build`),
reporter la copie à jour ici (`cp /home/claude/build/<fichier> tools/build-sources/build/<fichier>`,
puis commit) pour que le correctif survive à la session. Idem pour toute modification des pages
sources dans `/home/claude/src` → `tools/build-sources/src/`.

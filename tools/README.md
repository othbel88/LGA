# tools/

Outils de build non versionnés ailleurs (`/home/claude/build` et `/home/claude/src` ne sont
pas des dépôts Git — voir TECHNICAL-ARCHITECTURE.md). Conservés ici pour survivre aux
réinitialisations de session.

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

## build-sources/

Copies de sauvegarde des 4 fichiers sources réels du générateur, qui vivent normalement dans
`/home/claude/build` (non versionné, voir TECHNICAL-ARCHITECTURE.md) et seraient perdus en cas
de réinitialisation de session : `build.py`, `rooms_data.py`, `main.js`, `style.css`.

**Mise à jour du 25/11/2026** : conservées ici après plusieurs correctifs réels appliqués à ces
fichiers (contraste du header sur les fiches chambre, dédoublonnage des galeries, grammaire et
ordre des lits + configuration alternative twin confirmée sur 6 chambres, encart éditorial
Grenat/Grenadine, libellés). Si une session future ne retrouve pas ces correctifs déjà en place
dans `/home/claude/build`, c'est que la session a été réinitialisée : restaurer cette copie-ci
AVANT de reconstruire, plutôt que de recréer les fichiers de mémoire (qui réintroduirait les
anciens bugs déjà corrigés et vérifiés) :

    cp tools/build-sources/build.py tools/build-sources/rooms_data.py tools/build-sources/main.js /home/claude/build/
    cp tools/build-sources/style.css /home/claude/build/style.css

**Piège connu** : `/home/claude/src/css/style.css` et `/home/claude/src/js/main.js` sont des
fichiers DÉCOYS, obsolètes et non utilisés par le build réel — ne jamais les éditer ni les
confondre avec les fichiers ci-dessus. Le build réel copie toujours depuis `/home/claude/build`
(`style.css`, `main.js`) vers la sortie, jamais depuis `/home/claude/src/css` ou `/home/claude/src/js`
pour ces deux fichiers précis (confirmé par lecture directe de `build.py`, fonction qui copie
via `shutil.copy2(os.path.join(BUILD, 'style.css'), ...)` / `os.path.join(BUILD, 'main.js')`).

Après toute modification de l'un de ces 4 fichiers dans `/home/claude/build`, repartir cette
copie à jour ici (`cp /home/claude/build/<fichier> tools/build-sources/<fichier>`, puis commit)
pour que le correctif survive à la session.

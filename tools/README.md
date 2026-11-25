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

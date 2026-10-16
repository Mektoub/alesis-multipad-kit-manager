# Limites connues

Le format des sauvegardes a été rétro-ingénié à partir de quelques fichiers réels.
Ce qui suit n'est pas encore couvert ou vérifié.

## Sur l'appareil

- Les sauvegardes produites par l'outil n'ont pas encore été rechargées sur
  l'appareil. **Toujours garder une copie de la sauvegarde d'origine.**
- Les samples ajoutés par l'outil n'ont pas encore été écoutés sur l'appareil.

## Kits

- **Kits `KITC`** (format écrit par l'appareil quand on enregistre un kit) : pour
  les pads 1 à 8, seules les valeurs sont stockées, et certaines zones sont
  recouvertes par d'autres structures dont le rôle est inconnu. Les valeurs y
  restent lisibles et modifiables ; seul l'octet valeur est réécrit.
- **Emplacements 10 à 24** : leur correspondance exacte avec les déclencheurs
  externes et les pédales n'est pas vérifiée.
- Plusieurs paramètres ne sont pas encore identifiés (voir
  [Paramètres](parametres.md#paramètres-non-identifiés)), ni les réglages du kit
  autres que le nom, le volume et le tempo (signature rythmique, logo, effets).

## Samples

- Ajout vérifié jusqu'à l'id 8099 (dossier `080`). Au-delà, l'outil refuse.
- Supprimer ou remplacer un sample n'est pas pris en charge.
- Les samples d'usine ne figurent pas dans les sauvegardes : on ne peut ni les
  écouter ni les exporter.
- Les en-têtes `.had` tronquent les noms à 16 caractères ; `samples.json` donne
  les noms complets.

## Sauvegardes `.fac`

Elles ne contiennent que des kits : on ne peut pas y ajouter de samples.

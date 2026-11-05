# Ajouter un sample

[English](../en/adding-a-sample.md) · **Français**

Les samples ne peuvent être ajoutés qu'à une sauvegarde `.bkf`
(*Save All User Kits*), la seule qui contienne les samples utilisateur.

## Format requis

WAV PCM **16 bits, 44,1 kHz**, mono ou stéréo, comme pour un import sur l'appareil.
Le fichier est copié tel quel, sans conversion. Un WAV dans un autre format est
refusé avec un message qui indique le format reçu.

## Avec l'éditeur web

Dans la fenêtre de choix d'un sample (bouton du sample d'une wave), glisser-déposer
le fichier dans la zone *Ajouter un WAV* ou cliquer dessus. Le sample est ajouté
puis choisi pour la wave en cours. Voir [Éditeur web](web-editor.md).

## En ligne de commande

1. Exporter la sauvegarde (voir [Modifier un kit](editing-a-kit.md)).
2. Déposer le fichier dans le dossier `wav/` de l'export, par exemple
   `mes_kits/wav/Mon Snare.wav`.
3. Y faire référence par son nom, sans `.wav`, dans un kit :

   ```json
   "wave_a": { "sample": "Mon Snare" }
   ```

4. Lancer l'import : le sample est ajouté, puis les kits sont appliqués.

```bash
python3 -m strike_kits import Backup001.bkf mes_kits -o Backup002.bkf
# sample 'Mon Snare' ajouté (id 8073)
```

## Règles

- Le nom du sample est celui du fichier. Il doit être unique : l'appareil
  ajoute `_id` aux noms en double, l'outil refuse.
- Un WAV du dossier `wav/` est **ignoré** si son nom existe déjà parmi les samples,
  ou si son contenu est identique à celui d'un sample utilisateur. Le dossier `wav/`
  produit par l'export peut donc rester en place, même si on renomme un fichier :
  on peut relancer l'import autant de fois que nécessaire sans créer de doublon.
- Le sample reçoit l'id libre suivant (8073, 8074…) et rejoint la catégorie
  *User > New Sample*, comme un import fait sur l'appareil.
- Les règles appliquées (fichiers `.had`, cinq listes d'index, compteurs) ont été
  relevées sur une sauvegarde faite par l'appareil avant et après un import :
  l'outil reproduit ce résultat octet pour octet. Détails :
  [ajout d'un sample](bkf-format.md#ajout-dun-sample-observé-sur-lappareil).

## Renommer un sample

Dans l'éditeur, le bouton ✎ du gestionnaire de samples (bouton *Samples* de
l'en-tête) renomme un sample utilisateur ; les samples d'usine ne peuvent pas être renommés. Le nouveau nom
suit les mêmes règles qu'à l'ajout (unique, 127 caractères au plus, latin-1). Les
kits désignent les samples par leur id : ils ne changent pas.

- Le renommage n'a **pas été observé sur l'appareil**. L'outil applique les règles
  de l'ajout : le nom complet change dans `wave_list_sort_name.lst`, où l'entrée
  est déplacée à sa nouvelle place alphabétique, et le nom tronqué à 16 caractères
  change dans le `.had`. Détails :
  [renommage d'un sample](bkf-format.md#renommage-dun-sample-non-observé).
- Un export JSON fait avant le renommage désigne le sample par son ancien nom :
  le réimporter échoue (« sample introuvable »). Refaire l'export, ou remplacer le
  nom par l'id dans le JSON.

## Supprimer un sample

Dans le gestionnaire de samples, la corbeille supprime un sample utilisateur, après
confirmation. Si des kits l'utilisent, l'alerte liste les kits et pads concernés :
après la suppression, ces pads n'ont plus de sample. L'historique des modifications
est vidé.

- La suppression reproduit octet pour octet une sauvegarde faite par l'appareil
  avant et après la suppression d'un sample. Détails :
  [suppression d'un sample](bkf-format.md#suppression-dun-sample-observé-sur-lappareil).
- L'appareil, lui, laisse les kits pointer vers le sample supprimé ; l'outil les
  nettoie.
- Après une suppression, l'ajout d'un sample est refusé tant que l'id que lui
  donnerait l'appareil n'a pas été observé (« table des samples non contiguë »).

## Limites

- Ajout vérifié jusqu'à l'id 8099 (dossier `080`). Au-delà, l'outil refuse par
  prudence : la façon dont l'appareil nomme les dossiers suivants n'a pas été observée.
- Remplacer le WAV d'un sample n'est pas pris en charge.
- Ajouter un sample après une suppression n'est pas encore possible (voir
  [Supprimer un sample](#supprimer-un-sample)).
- Les samples d'usine ne sont pas dans la sauvegarde : on ne peut ni les écouter ni
  les exporter, seulement les référencer par leur id ou leur nom.

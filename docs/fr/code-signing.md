# Code signing policy (politique de signature du code)

[English](../en/code-signing.md) · **Français**

Signature du code gratuite fournie par [SignPath.io](https://about.signpath.io/),
certificat délivré par [SignPath Foundation](https://signpath.org/).

> La candidature auprès de SignPath Foundation est en cours : tant qu'elle n'est
> pas acceptée, les paquets Windows ne sont pas signés (voir
> [Application de bureau](desktop-app.md#paquets-windows-et-macos)).

## Ce qui est signé

Seuls les paquets Windows de l'application de bureau, publiés dans les
[releases GitHub](https://github.com/Mektoub/alesis-multipad-kit-manager/releases) :

- l'installateur `alesis-kit-manager-X.Y.Z-win-x64-setup.exe` ;
- les exécutables construits à partir de ce dépôt qu'il contient
  (`alesis-kit-manager.exe`, `alesis-kit-manager-server.exe`).

Ils sont construits par GitHub Actions, sur des runners hébergés par GitHub, à
partir des sources de ce dépôt au tag de la version
(`.github/workflows/release.yml` et `build.yml`), puis soumis à SignPath. Les
composants tiers (Electron, Python et leurs bibliothèques) sont inclus tels que
publiés par leurs auteurs et ne sont pas signés par ce projet. Les paquets Linux
et macOS ne sont pas signés par SignPath.

## Rôles de l'équipe

| Rôle | Membres |
|---|---|
| Auteurs et relecteurs (*committers and reviewers*) | [Mektoub](https://github.com/Mektoub) |
| Approbateurs (*approvers*) | [Mektoub](https://github.com/Mektoub) |

- Les auteurs peuvent modifier directement les sources du dépôt.
- Toute modification proposée par une autre personne (pull request) est relue par un auteur avant d'être fusionnée.
- Chaque demande de signature est approuvée à la main par un approbateur, à chaque version.
- Tous les membres utilisent l'authentification multifacteur sur GitHub et sur SignPath.

## Confidentialité

Ce programme ne transmet aucune information à d'autres systèmes en réseau, sauf
à la demande explicite de l'utilisateur ou de la personne qui l'installe ou
l'utilise.

L'éditeur lance un serveur local, joignable uniquement depuis l'ordinateur
lui-même (`127.0.0.1`) ; les sauvegardes, kits et samples restent sur
l'ordinateur. L'application n'envoie aucune statistique d'utilisation.

La recherche des mises à jour est le seul accès au réseau, et seulement avec
l'accord de l'utilisateur : au premier lancement, l'application demande s'il
faut rechercher les mises à jour à chaque lancement (modifiable dans les
*Préférences*), et *Aide › Rechercher des mises à jour…* recherche à la demande.
Une recherche télécharge auprès de GitHub (`github.com`) la description de la
dernière release ; un téléchargement y récupère le nouveau paquet. Seules les
données habituelles d'une requête (adresse du fichier demandé, adresse IP)
parviennent à GitHub, selon sa
[déclaration de confidentialité](https://docs.github.com/fr/site-policy/privacy-policies/github-general-privacy-statement).
Voir [Mises à jour](desktop-app.md#mises-à-jour).

## Désinstallation

L'installateur Windows ajoute un programme de désinstallation : *Paramètres ›
Applications › Applications installées*, *Alesis Kit Manager*, *Désinstaller*.
L'archive `.zip` se supprime en effaçant son dossier. Les préférences restent
dans `%APPDATA%\AlesisKitManager\`, à supprimer à la main (voir
[Préférences](web-editor.md#préférences)).

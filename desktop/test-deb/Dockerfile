# Système Ubuntu propre pour tester l'installation du paquet .deb
# (./dev.sh test-deb). Seuls les outils du test sont ajoutés : ni Python ni
# Node, pour vérifier que l'application installée n'en a pas besoin.
FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl xvfb xauth desktop-file-utils \
    && useradd --create-home testeur
# les listes de paquets restent dans l'image : apt install ./paquet.deb en a besoin

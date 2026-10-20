"""Point d'entrée du serveur figé par PyInstaller (desktop/server.spec) :
mêmes options que `python -m editor`."""

from editor.__main__ import main

if __name__ == "__main__":
    main()

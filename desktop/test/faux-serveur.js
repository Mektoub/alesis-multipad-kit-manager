// Faux serveur Python pour les tests : se comporte selon FAKE_MODE.
//   ready   annonce le port après une ligne parasite, puis attend la fin de stdin ;
//           refuse de démarrer sans le jeton attendu (FAKE_TOKEN)
//   crash   écrit une erreur et s'arrête avec le code 2
//   silent  ne répond jamais
//   stubborn annonce le port mais ignore la fermeture de stdin
const mode = process.env.FAKE_MODE;
if (mode === "ready" && process.env.KITMANAGER_TOKEN !== process.env.FAKE_TOKEN) {
  console.error(`jeton inattendu : ${process.env.KITMANAGER_TOKEN}`);
  process.exit(3);
}
if (mode === "crash") {
  console.error("Erreur : fichier illisible");
  process.exit(2);
}
if (mode === "ready" || mode === "stubborn") {
  console.log("ligne parasite");
  console.log(JSON.stringify({ ready: true, port: 4321 }));
}
if (mode === "ready") {
  process.stdin.resume();
  process.stdin.on("end", () => process.exit(0));
} else {
  setInterval(() => {}, 1000);
}

// Rend icon.svg en PNG 512×512 (fond transparent) avec Electron, sans fenêtre visible :
//   cd desktop && npx electron build-resources/render-icon.cjs build-resources/icon.svg build-resources/icon.png
const { app, BrowserWindow } = require("electron");
const fs = require("node:fs");
const [svg, png] = process.argv.slice(-2);
app.disableHardwareAcceleration();
app.whenReady().then(async () => {
  const win = new BrowserWindow({ width: 512, height: 512, show: false, transparent: true, frame: false,
    useContentSize: true, webPreferences: { offscreen: true } });
  const html = `<html><body style="margin:0;background:transparent">${fs.readFileSync(svg, "utf8")}</body></html>`;
  await win.loadURL("data:text/html;charset=utf-8," + encodeURIComponent(html));
  await new Promise((r) => setTimeout(r, 500));
  const image = await win.webContents.capturePage({ x: 0, y: 0, width: 512, height: 512 });
  fs.writeFileSync(png, image.toPNG());
  console.log("écrit", png, image.getSize());
  app.quit();
});

import "./lib/fake-desktop.js"; // avant api.js, qui lit window.kitManagerDesktop
import { mount } from "svelte";
import "./app.css";
import App from "./App.svelte";

export default mount(App, { target: document.getElementById("app") });

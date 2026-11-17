// Screenshot pages at 2x with headless Chromium, over the DevTools protocol.
// tools/screenshots.py drives it; it reads a JSON list of shots:
//
//   node tools/capture.mjs shots.json
//   [{ "url": ..., "width": 560, "height": 500, "setup": "<JS, may return a promise>",
//      "wait": 600, "transparent": false, "out": "path.png" }]
//
// Chromium is /Applications/Chromium.app unless CHROMIUM names another.

import { spawn } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const CHROMIUM = process.env.CHROMIUM || "/Applications/Chromium.app/Contents/MacOS/Chromium";
const shots = JSON.parse(readFileSync(process.argv[2], "utf8"));
const profile = mkdtempSync(join(tmpdir(), "exam-timeline-shots-"));
const chrome = spawn(
  CHROMIUM,
  ["--headless=new", "--remote-debugging-port=0", `--user-data-dir=${profile}`, "--hide-scrollbars",
    "--no-first-run", "--no-default-browser-check", "--allow-file-access-from-files", "about:blank"],
  { stdio: ["ignore", "ignore", "pipe"] },
);
const done = async () => {
  if (chrome.exitCode === null && chrome.signalCode === null) {
    const exited = new Promise((resolve) => chrome.once("exit", resolve));
    chrome.kill();
    await exited;
  }
  rmSync(profile, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 });
};

try {
  const wsUrl = await new Promise((resolve, reject) => {
    let err = "";
    chrome.stderr.on("data", (d) => {
      err += d;
      const m = err.match(/DevTools listening on (ws:\/\/\S+)/);
      if (m) resolve(m[1]);
    });
    chrome.on("exit", (code) => reject(new Error(`Chromium exited (${code}):\n${err}`)));
  });
  const ws = new WebSocket(wsUrl);
  await new Promise((resolve) => ws.addEventListener("open", resolve, { once: true }));
  let next = 0;
  const pending = new Map();
  const events = new Set();
  ws.addEventListener("message", (e) => {
    const m = JSON.parse(e.data);
    const p = pending.get(m.id);
    if (p) {
      pending.delete(m.id);
      m.error ? p.reject(new Error(m.error.message)) : p.resolve(m.result);
    } else events.forEach((f) => f(m));
  });
  const send = (method, params = {}, sessionId) => new Promise((resolve, reject) => {
    const id = ++next;
    pending.set(id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params, sessionId }));
  });
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  for (const s of shots) {
    const { targetId } = await send("Target.createTarget", { url: "about:blank" });
    const { sessionId } = await send("Target.attachToTarget", { targetId, flatten: true });
    const call = (method, params) => send(method, params, sessionId);
    await call("Page.enable");
    await call("Emulation.setFocusEmulationEnabled", { enabled: true }); // focus events, as in a front window
    await call("Emulation.setDeviceMetricsOverride", { width: s.width, height: s.height, deviceScaleFactor: 2, mobile: false });
    if (s.transparent) await call("Emulation.setDefaultBackgroundColorOverride", { color: { r: 0, g: 0, b: 0, a: 0 } });
    const loaded = new Promise((resolve) => {
      const f = (m) => {
        if (m.sessionId === sessionId && m.method === "Page.loadEventFired") { events.delete(f); resolve(); }
      };
      events.add(f);
    });
    await call("Page.navigate", { url: s.url });
    await loaded;
    await sleep(300);
    if (s.setup) {
      const r = await call("Runtime.evaluate", { expression: s.setup, awaitPromise: true, returnByValue: true });
      if (r.exceptionDetails) {
        throw new Error(`${s.out}: ${r.exceptionDetails.exception?.description ?? r.exceptionDetails.text}`);
      }
    }
    await sleep(s.wait ?? 600);
    const { data } = await call("Page.captureScreenshot", { format: "png" });
    writeFileSync(s.out, Buffer.from(data, "base64"));
    await send("Target.closeTarget", { targetId });
  }
  ws.close();
} finally {
  await done();
}

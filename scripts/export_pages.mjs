import { cp, mkdir, rm, writeFile } from "node:fs/promises";
import { pathToFileURL } from "node:url";
import path from "node:path";

const root = process.cwd();
const repository = "lunarbank-remittance-intelligence";
const basePath = `/${repository}`;
const workerUrl = pathToFileURL(path.join(root, "dist/server/index.js"));
workerUrl.searchParams.set("export", Date.now().toString());
const { default: worker } = await import(workerUrl.href);

const response = await worker.fetch(
  new Request("https://karthikxyz.github.io/", { headers: { accept: "text/html" } }),
  { ASSETS: { fetch: async () => new Response("Not found", { status: 404 }) } },
  { waitUntil() {}, passThroughOnException() {} },
);
if (!response.ok) throw new Error(`Static render failed with status ${response.status}`);

let html = await response.text();
for (const asset of ["assets", "analytics.json", "favicon.svg", "file.svg", "globe.svg", "og.png", "window.svg"]) {
  html = html.replaceAll(`/${asset}`, `${basePath}/${asset}`);
}
html = html.replaceAll("http://localhost:3000", `https://karthikxyz.github.io${basePath}`);

const output = path.join(root, "docs");
await rm(output, { recursive: true, force: true });
await mkdir(output, { recursive: true });
await cp(path.join(root, "dist/client"), output, { recursive: true });
await writeFile(path.join(output, "index.html"), html, "utf8");
await writeFile(path.join(output, ".nojekyll"), "", "utf8");
console.log(`Exported GitHub Pages site to ${output}`);

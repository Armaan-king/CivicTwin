// The committed run lives in data/fixtures. Vite can only serve what is under public/,
// so it is copied at dev and build time rather than committed twice. Two copies in git
// drift the moment someone regenerates and forgets to sync.
import { copyFileSync, mkdirSync, existsSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const src = resolve(here, "../../data/fixtures/demo_run.json");
const dest = resolve(here, "../public/fixtures/demo_run.json");

if (!existsSync(src)) {
  console.error(
    `\nNo run fixture at ${src}\nGenerate one first:  python scripts/make_fixture.py\n`
  );
  process.exit(1);
}
mkdirSync(dirname(dest), { recursive: true });
copyFileSync(src, dest);
console.log("fixture synced -> public/fixtures/demo_run.json");

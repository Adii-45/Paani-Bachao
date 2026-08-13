import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const frontendRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const repositoryRoot = path.resolve(frontendRoot, "..");
const eslintBin = path.join(frontendRoot, "node_modules", "eslint", "bin", "eslint.js");
const files = process.argv.slice(2).map((file) =>
  path.relative(frontendRoot, path.resolve(repositoryRoot, file)),
);

const result = spawnSync(process.execPath, [eslintBin, ...files], {
  cwd: frontendRoot,
  stdio: "inherit",
});

if (result.error) {
  console.error("Unable to run ESLint. Install frontend dependencies with `npm ci` first.");
  console.error(result.error.message);
  process.exit(1);
}

process.exit(result.status ?? 1);

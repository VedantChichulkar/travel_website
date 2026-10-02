import assert from "node:assert/strict";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { extname, join } from "node:path";
import test from "node:test";

const roots = ["app", "src/components", "src/lib", "src/data"];
const sourceExtensions = new Set([".ts", ".tsx", ".json"]);

function sourceFiles(path) {
  if (statSync(path).isDirectory()) {
    return readdirSync(path).flatMap((name) => sourceFiles(join(path, name)));
  }
  return sourceExtensions.has(extname(path)) ? [path] : [];
}

test("customer-facing source does not contain the former display brand", () => {
  const offenders = roots
    .flatMap(sourceFiles)
    .filter((path) => /\bVayora\b/.test(readFileSync(path, "utf8")));

  assert.deepEqual(offenders, []);
});

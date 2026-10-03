import assert from "node:assert/strict";
import { existsSync, readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";
import nextConfig from "../next.config.ts";

function sources(path) {
  return readdirSync(path, { withFileTypes: true }).flatMap((entry) => {
    const file = join(path, entry.name);
    return entry.isDirectory() ? sources(file) : /\.(tsx?|json)$/.test(file) ? [file] : [];
  });
}

test("legacy Experiences redirects permanently without retaining a content page", async () => {
  const redirects = await nextConfig.redirects();
  assert.deepEqual(redirects.find((rule) => rule.source === "/experiences"), {
    source: "/experiences", destination: "/destinations", permanent: true,
  });
  assert.equal(existsSync("app/experiences/page.tsx"), false);
});

test("public source does not advertise the retired route", () => {
  const offenders = ["app", "src"].flatMap(sources).filter((file) => readFileSync(file, "utf8").includes("/experiences"));
  assert.deepEqual(offenders, []);
});

test("homepage discovery uses the existing nine Interests", () => {
  const manifest = JSON.parse(readFileSync("src/data/discovery-media-manifest.json", "utf8"));
  const copy = readFileSync("src/data/place-interests.ts", "utf8");
  for (const slug of Object.keys(manifest.interests)) assert.ok(copy.includes(`"${slug}": {`));
  assert.equal(Object.keys(manifest.interests).length, 9);
  const homepage = readFileSync("src/components/InterestsSection.tsx", "utf8");
  assert.ok(homepage.includes("KNOWN_INTEREST_SLUGS.map"));
  assert.ok(homepage.includes("`/explore/${slug}`"));
});

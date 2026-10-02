import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";
import { dirname, join, normalize } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const frontendRoot = join(dirname(fileURLToPath(import.meta.url)), "..");
const manifest = JSON.parse(readFileSync(join(frontendRoot, "src/data/discovery-media-manifest.json"), "utf8"));

test("manifest inventories every discovery entity", () => {
  assert.equal(Object.keys(manifest.places).length, 49);
  assert.equal(Object.keys(manifest.stories).length, 10);
  assert.equal(Object.keys(manifest.interests).length, 9);
});

test("every declared public asset exists and has usable provenance", () => {
  const assets = [manifest.globalFallback, ...Object.values(manifest.interests)];
  for (const asset of assets) {
    assert.match(asset.asset, /^\/images\//);
    const localPath = normalize(join(frontendRoot, "public", asset.asset));
    assert.equal(existsSync(localPath), true, `${asset.asset} must exist`);
    assert.ok(asset.alt.trim());
    const provenance = manifest.provenance[asset.provenanceId];
    assert.ok(provenance, `${asset.provenanceId} must resolve`);
    assert.ok(provenance.source.trim());
    assert.ok(provenance.usageBasis.trim());
    assert.equal(provenance.documentary, false);
  }
});

test("fallback hierarchy is deterministic", () => {
  for (const [identity, record] of [...Object.entries(manifest.places), ...Object.entries(manifest.stories)]) {
    assert.equal(record.status, "FALLBACK", `${identity} has no approved specific asset`);
    assert.ok(manifest.interests[record.fallbackInterest], `${identity} must resolve to an Interest fallback`);
  }
  assert.equal(manifest.globalFallback.status, "FALLBACK");
  assert.ok(manifest.globalFallback.asset);
});

test("priority queue covers all Places without claiming tourism rank", () => {
  const tiers = Object.values(manifest.places).map((record) => record.priorityTier);
  assert.equal(tiers.every((tier) => [1, 2, 3].includes(tier)), true);
  assert.equal(tiers.filter((tier) => tier === 1).length, 13);
});

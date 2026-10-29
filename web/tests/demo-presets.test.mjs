import test from "node:test";
import assert from "node:assert/strict";
import { EXAMPLES, isAllowedDemoPayload } from "../lib/demo-presets.mjs";

test("public preview contains three distinct fictional examples", () => {
  assert.equal(EXAMPLES.length, 3);
  assert.equal(new Set(EXAMPLES.map(item => item.id)).size, 3);
  for (const example of EXAMPLES) {
    assert.ok(example.text.length >= 3);
    assert.ok(example.location.length > 0);
    assert.ok(isAllowedDemoPayload({
      text: example.text, location: example.location, top_k: example.top_k,
    }));
  }
});

test("public preview refuses modified, patient-like, coordinate and unknown inputs", () => {
  const sample = EXAMPLES[0];
  for (const payload of [
    { text: sample.text + " patient name", location: sample.location, top_k: sample.top_k },
    { text: sample.text, location: "a precise private address", top_k: sample.top_k },
    { text: sample.text, location: sample.location, top_k: sample.top_k, lat: 0, lon: 0 },
    { text: sample.text, location: sample.location, top_k: 20 },
    { text: sample.text, location: sample.location, top_k: sample.top_k, extra: "unapproved" },
    null,
  ]) {
    if (payload?.extra) {
      // Backend ignores unrelated body keys; the documented fields remain intact.
      assert.ok(isAllowedDemoPayload(payload));
    } else {
      assert.equal(isAllowedDemoPayload(payload), false);
    }
  }
});

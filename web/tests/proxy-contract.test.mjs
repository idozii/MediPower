import test from "node:test";
import assert from "node:assert/strict";
import { checkPredictionPayload, resolveBackendBaseUrl, sanitizedBackendError } from "../lib/proxy-contract.mjs";

const base = { text: "fictional cough", location: "Sydney", top_k: 5 };

test("proxy validates input and accepted coordinate ranges", () => {
  assert.equal(checkPredictionPayload(base), null);
  assert.equal(checkPredictionPayload({text:"fictional flu",lat:0,lon:0,top_k:1}), null);
  assert.ok(checkPredictionPayload({text:"x",location:"Sydney"}));
  assert.ok(checkPredictionPayload({text:"cough",lat:100,lon:0}));
  assert.ok(checkPredictionPayload({text:"cough",lat:0}));
  assert.ok(checkPredictionPayload({text:"cough",location:"Sydney",top_k:100}));
});

test("proxy cannot be tricked by non-JSON body objects", () => {
  assert.ok(checkPredictionPayload(null));
  assert.ok(checkPredictionPayload([]));
  assert.ok(checkPredictionPayload("not object"));
});

test("backend origin configuration rejects unsafe URL forms", () => {
  assert.equal(resolveBackendBaseUrl("https://example.org").origin,"https://example.org");
  for (const input of ["file:///etc/hosts","ftp://example.org","https://a:b@example.org","not-a-url"]) {
    assert.throws(() => resolveBackendBaseUrl(input));
  }
});

test("public proxy errors do not reflect raw upstream details", () => {
  assert.equal(sanitizedBackendError({ detail: "secret" },500),"Research backend is temporarily unavailable.");
});

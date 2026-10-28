import test from "node:test";
import assert from "node:assert/strict";
import { makeRequestBody, validateResearchForm, formatRankingScore } from "../lib/research-form.mjs";

const base = { text: "fictional cough", location: "Sydney CBD", lat: "", lon: "", top_k: 5 };

test("city payload uses explicit location", () => {
  assert.equal(validateResearchForm(base), null);
  assert.deepEqual(makeRequestBody(base), {text:"fictional cough",location:"Sydney CBD",top_k:5});
});

test("paired coordinates including zero", () => {
  assert.deepEqual(makeRequestBody({...base,location:"",lat:"0",lon:"0"}),
    {text:"fictional cough",lat:0,lon:0,top_k:5});
});

test("invalid input is rejected before request", () => {
  for(const row of [
    {...base,text:"x"},
    {...base,text:"x".repeat(2001)},
    {...base,location:""},
    {...base,location:"",lat:"-91",lon:"151"},
    {...base,location:"",lat:"0",lon:""},
    {...base,top_k:21}
  ]) assert.ok(validateResearchForm(row));
});

test("missing scores are not fabricated", () => {
  assert.equal(formatRankingScore(null), "Not available");
  assert.equal(formatRankingScore(""), "Not available");
  assert.equal(formatRankingScore(0.12345), "0.123 / 1");
});

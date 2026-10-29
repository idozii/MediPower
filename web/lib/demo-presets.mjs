/** Controlled public demo presets. Fictional research examples only. */
export const EXAMPLES = Object.freeze([
  Object.freeze({
    id: "respiratory",
    icon: "activity",
    label: "Respiratory symptoms",
    text: "fever, cough, body aches, sore throat",
    location: "Melbourne",
    top_k: 5,
  }),
  Object.freeze({
    id: "headache",
    icon: "layers",
    label: "Headache scenario",
    text: "recurring throbbing headache with sensitivity to light",
    location: "Sydney CBD",
    top_k: 5,
  }),
  Object.freeze({
    id: "abdominal",
    icon: "map",
    label: "Abdominal discomfort",
    text: "lower abdominal pain with nausea",
    location: "Brisbane",
    top_k: 5,
  }),
]);

export function isAllowedDemoPayload(payload) {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) return false;
  if (Object.keys(payload).some(key => !["text", "location", "top_k"].includes(key))) return false;
  return EXAMPLES.some(example =>
    payload.text === example.text &&
    payload.location === example.location &&
    payload.top_k === example.top_k &&
    (payload.lat === undefined || payload.lat === null) &&
    (payload.lon === undefined || payload.lon === null)
  );
}

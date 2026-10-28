# M3: when the official Figshare download returns HTTP 403

The primary author source is https://github.com/mila-iqia/ddxplus and its official English Figshare release (article 22687585, version 2). 403 can indicate access restrictions/CDN/regional filtering; **do not assume the original release is no longer valid**. Try the public read-only Figshare article metadata endpoint from your own terminal:

    python -c "import urllib.request; u='https://api.figshare.com/v2/articles/22687585'; r=urllib.request.urlopen(u, timeout=20); print(r.status, len(r.read()))"

If this also yields 403 or times out, a community-maintained Hugging Face mirror is available at https://huggingface.co/datasets/aai530-group6/ddxplus/tree/main . This is NOT published by Mila. It advertises CC BY 4.0 and holds English validation CSV, evidence definitions and condition definitions. The files may not be byte-identical to the Figshare record; do not describe them as officially verified or clinically representative.

## Explicit opt-in local fallback

    git pull --ff-only
    python -m pip install huggingface_hub
    python -m research.m3_fetch_dev_data --accept-community-mirror

This downloads only these three files under research/private_data/ddxplus, which is ignored by Git:
- validate.csv (87.4 MB according to the Hugging Face page; observed SHA256: b84733533bff01daa1d47d27a0cd4d684bb54a0fc20d80aaee1250ff8ff989ed)
- release_evidences.json
- release_conditions.json

**No test or training patient data are downloaded.** The downloader resolves and pins the community dataset commit SHA, validates validation.csv against the explicitly documented SHA256, and writes a local private provenance summary. It checks metadata counts but does not prove equivalence to the authors' official Figshare release. Review any Hugging Face access or research-purpose terms before clicking accept.

## Audit before mapping

    python -m research.m3_source_preflight --patients research/private_data/ddxplus/validate.csv --evidences research/private_data/ddxplus/release_evidences.json --conditions research/private_data/ddxplus/release_conditions.json --expected-patients-sha256 b84733533bff01daa1d47d27a0cd4d684bb54a0fc20d80aaee1250ff8ff989ed

Next generate PENDING (not approved) mapping candidates:

    python -m research.suggest_ddxplus_mappings --conditions research/private_data/ddxplus/release_conditions.json --catalog app/data/diseases.csv --out research/private_data/ddxplus_mapping_candidates.csv

The reviewed mapping file and external evaluation are intentionally blocked until an appropriate reviewer validates diagnosis equivalence and catalog coverage; similarity candidates do NOT satisfy that condition. No DDXPlus test split may be accessed for tuning.

Only share **aggregate** printed audit results or metadata/hashes, not raw patient rows. Keep research/private_data out of GitHub and screenshots.

## If Hugging Face also fails
The official Figshare API metadata (above) may work even if the browser page is blocked. Contact the dataset authors/host or use another network permitted by their access terms. Do not fetch unofficial random datasets or treat a community mirror as independently verified official data.

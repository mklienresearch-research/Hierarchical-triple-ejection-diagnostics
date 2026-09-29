# Kaggle datasets verification log (12/12, 2026-09-26)

Source: user-run `os.walk` + sha256 over `/kaggle/input/datasets/klienm/*`
(Kaggle notebook mount; `.virtual_documents/__notebook_source__.ipynb` artifacts excluded).
All hashes below are local ground truth supplied by the dataset owner.

## Full inventory (114 files)

### 3000t-out
- `ece95247a8b3ab9c85428f78c13071b9b82f6ab5f0b2e9e0f07057ac74cd55e5` 3604219 `v2out/chunk_tail_0_of_2.npz`
- `7d224617635e9f07e2502de13afceaa7a2d8318a6f14a647e2e4657cd9cf1e0c` 209 `v2out/chunk_tail_0_of_2_meta.json`

### 3000t-outpart-2
- `5029ad433ce368a0763d51322976106e89a76e67ea77b1f1b9ddfee446d7c4db` 3603997 `chunk_tail_1_of_2.npz`
- `69cea0d09ccf4ddbc562af012857d6968d4225292c3726cc69f0c00a099c1d7f` 227 `chunk_tail_1_of_2_meta.json`

### analysis — `analysis_final_4core/` and `final_analysis_all_jsons/` are BYTE-IDENTICAL (dup)
Per-folder contents (19 files each):
- `fb83d728ee17140733225bf11611d433616e640a767199e113ed5e45cc06dd34` 406 `analysis_audit.json`
- `f19251031b5cea7398de419dc26731a07b5e217abd1eb32c33faa9e012e2906d` 2189 `boundary_causal.json`
- `2d081d9a8c4e344317789a1377265696ffaab56b5cbea0a7a399ce545c8f879d` 284 `boundary_decision.json`
- `7e22aed897bf6f6ba9034a2cb609b3b933a9ce4405fa9d557cf14d757fb2e90f` 269 `boundary_ood.json`
- `8b18fb7a02d6809c1f230941b306a9e01aa17b9c02c121c3b7a21e592a305281` 1207 `cox_hazards.json`
- `cf10147e57948710dc561c9cc6b9ab462d63da89060d1915062bd8f63ae85011` 4191 `enc_causal.json`
- `0cef8ac71eb397c76020b7a3a44be5cc2ba6935b6f37a7704ed6f4c6cc8ee558` 692 `enc_conditional.json`
- `b4a30995592653b3d2286e8e2562e2acec257e8493321ed293e7503f92e47474` 302 `enc_decision.json`
- `fd4eee1279123902da0916a4ec5930fea57ddffec15464df62ad53e854ccf403` 6970 `enc_multiclass.json`
- `3a2d581f77a35ef8303ea35e2d03649a5c2a474db18a3d4c23d3ad6167ff405f` 676 `enc_multiclass_conditional.json`
- `17c934a650af8bf2f422fe3f01068ccf08b5e6126bdae22dc9369661a5729e75` 372 `enc_multiclass_decision.json`
- `98f8af76561b0b3839ae5a145a391809ab4164fbcbe3f6bd274440439c678815` 965 `ma01_benchmark.json`
- `0540790157509822a5ac8ead36ceeca6af0eaacd7d30bbea2e615f19c79a9991` 28165 `report.json`
- `62c174c5b0d3328fe60137ce6cc00680509af3edf47fcd9f0108d58ac6c09c7b` 624 `spike_study.json`
- `93e4ea4baadbf45f56da7182b5212040b19c30f112225cbbdde44205be40d039` 2212 `triples_causal.json`
- `0fc7f94ca0a1bca9e2a321d049384eb143208f847e57566a6d7631a23463c81d` 284 `triples_decision.json`
- `50425d6c5867e89dbd5b298d401db2e4b5c6a13687bbac023497ce514d29a56d` 3990 `triples_multiclass.json`
- `c523548fd7149c87ad2e3fe3e336903b77eba89f94b308bf01c39286ecb611e0` 244 `triples_multiclass_decision.json`
- `32c97f013ab135911d4e3509a7c6fe2c28dbbf7b208fbe38096ada6b059b132c` 533 `tte_regression.json`

### attribution-growth (v1 — SUPERSEDED by v2, same filenames different bytes)
- `8591340cfdfaa280fe159412bc3083e665b840986a7258bff21e74074876e11d` 899 `OUTPUT_MANIFEST.json`
- `fb4d982f259d5f24195de7989ca80ece4e05a320fc46daae6609b86145121cfc` 2418 `attribution_growth_summary.json`
- `15c83386a81759d56f8498ffca9689c16c4673debb5eb4b90b5e954eeb0615c1` 14283 `boundary_joint_gain_bootstrap.npz`
- `b29244722b7d3a0ee7aa780f06ad051eaba9d12182089b654c8f30d41fdeceda` 1083 `boundary_joint_gain_growth.json`
- `ee3ead3254189a13ec0a2aebabdddfade026f9575c02410ceb4520dc52cd3334` 9798 `prospective_model_attribution.json`
- `410600333063ef0d388aaeb99322338a38abf90b09fea067bf0ca0b2bdc3a2ff` 13743 `triples_joint_gain_bootstrap.npz`
- `6bf94a36cfdfe12514bfbcc39a031a5b9a63e196a5fc5847690287ae6265f5f4` 1080 `triples_joint_gain_growth.json`

### attribution-growth-v2 (canonical)
- `2729e6f9b10bd912e74972b52566e8547f9c4913138e22933055c20bf12594de` 2151 `OUTPUT_MANIFEST.json`
- `cece639bec15ed9bffe2eb9df5fa0cf1758d2d020592b2db1b58d5323f8f22e5` 6428 `attribution_growth_summary.json`
- `3ebc277ca417c5be70812c5f3a4220d526f9327249c7d42583c0b3b9bf77b87a` 66562 `boundary_changing_inplay_risk_set_joint_bootstrap.npz`
- `aa545e1292e0815926f53a12993c1299d798cda85724a8a032ae509ad29cd6a8` 67231 `boundary_fixed_latest_landmark_cohort_joint_bootstrap.npz`
- `bdc1a8c32d146d56c06eff67f830acedff5e6d46432ced0a44a8868074fc9006` 2597 `boundary_joint_gain_growth.json`
- `fed578d6d63fc52ebe602eccba4da413a36e7e2057550d95a78111d9892f8701` 15600 `prospective_model_attribution.json`
- `01b5bbd84d7de4aed03a3b37e7146294c50b9f9b4b8dd72d98cc38d5ad2c5472` 13735 `triples_changing_inplay_risk_set_joint_bootstrap.npz`
- `1898124ed1b14eeb49b4413bb81bcf36f5f9a62f6749e14300d47e8a3d2b29ee` 64928 `triples_fixed_latest_landmark_cohort_joint_bootstrap.npz`
- `cfac02cf13e1c21b3da7057db3ca42dc5799bdd2d1c13526ea8f7cc9937c1fbc` 2584 `triples_joint_gain_growth.json`

### final-audit-expanded (25 files; 23/23 SHA256SUMS entries verified against this walk)
- `cca6a5e071005f68e3a5c0a3ffad0feb8045a69969a327a2ebd8acdf4a6a8430` 3263 `OUTPUT_MANIFEST.json`
- `693757b840216d17826e2dd75fd1d4aec15f0e8efa4ab9e2446a286b958e7a4e` 2186 `SHA256SUMS.txt`
- `d404ea752291f6a87082eafd4b959782fbef7f7b6a0a93a55997acd1b32b0f79` 969 `audit_summary.json`
- `ace43ff21d81178edecbb3c5c8bc9efb634448f2a2aa8b6002b353ef92e6a4f6` 7865 `boundary_landmark_fixed_cohort.json`
- `0be9bec8bc3b14d0977a7510aa7987775abb6be8db10316b427b9a480a66a1cd` 18307 `boundary_ood_inplay_corrected.json`
- `035577f5ecc88b32280f6a98d4c67b3cfc381b4f09d31aaaa34c6bbe553ea7f9` 40726 `boundary_parity.json`
- `f9b2a8332b932db93e56500e2535a298be7a67b63aceec422b8acd2cc1ada103` 1234 `boundary_retention.json`
- `e273d750522fdd318d9c0541c727136e1a45fb2d438224c3d906a8e8f9852301` 278207 `boundary_split_ids.npz`
- `ef91aec430777b79d74e0a2d5172e9dd05b76227327986b7679903085c9ef29c` 19114 `boundary_thresholds.json`
- `3d2fefab7ae5f55579f990146be881abb1161a13180ea802ba733f0a2cab9850` 695949 `boundary_untouched_test_scores.npz`
- `5ba34becb3df1623bb1b356a66f89d50f1911bcc03887431204dd9a0f752301a` 19648 `enc_conditional_inplay_corrected.json`
- `4f9b779d0be4e3bcd1959f30954ccbf7630d2cebeac09f30ee8254fa2045ac13` 15750 `enc_multiclass_conditional_inplay_corrected.json`
- `f588fccf228ef6bb74da7b5e5afc1b72e64b34d155c66ca647809e9e4b0b3cd0` 16131 `encounters_landmark_fixed_cohort.json`
- `a2a987aa31f8c7bd961e53f936d241e59d27300a0a91f3ce82ae6cbad1df17c7` 66137 `encounters_parity.json`
- `e08fc7bab23d060ae7cdb8d7ce123216411913a8f080ccaca0ee8cf0a5e26325` 2439 `encounters_retention.json`
- `6921d25724abbe302604f977ebad5a0aab5509be60b8a28d0a85edfc008d2642` 3156511 `encounters_split_ids.npz`
- `89234f2ff2178e3d62f288bcc8f320a7257708a0aae7ea7813f01c8eee4801d6` 32315 `encounters_thresholds.json`
- `c3328aaf8e925af1072af24cf5fcdfaf0f138e494cd74171005c104b1ee7c2fd` 29375549 `encounters_untouched_test_scores.npz`
- `ba7043e1e318e45b0afcbb55fc25a3a9adc9cfc964a86d2a31d10286686b23fb` 496 `negative_controls_final.json`
- `de90c4d2e03686b306716cdf06e55d55203e9c695c4de95cd6d83ea0e4906fad` 8039 `triples_landmark_fixed_cohort.json`
- `2f126f5100f5495090a6fc45cc91f62f5fd0abf61f991e69ea65fe148b77b8a5` 41005 `triples_parity.json`
- `b4b5224eda316c8769d0a8de1b7cf2883975caf8162bbed7185a903d5e0e0bf9` 1250 `triples_retention.json`
- `742e7b2ccd0dfefc6ca3b256ffe1aafa38c5910669426f881d7b803ad97113fb` 1514144 `triples_split_ids.npz`
- `d09d023f8094e63965cf58e8239bf678906051e009480761d1ebcf4ea8e6cfb8` 19321 `triples_thresholds.json`
- `5dd741e5384a240404cb28f68790228dcaaa78393fab900509fb985fa1642d14` 6068681 `triples_untouched_test_scores.npz`

### mergedtriples
- `187835e0b45964f8ef0c295952eb49569ce5a5f9c9ec779e490d35f7aa352687` 1817502996 `merged_triples.npz`
- `bc68fead0d42e01077767c35cc16c6cb069b667c2a4807caead29220b9774b82` 232266718 `merged_triples_series.pkl`

### posttail-survivalanalysis (`deeptail_final/`; 6/6 SHA256SUMS + manifest bytes+hash verified)
- `b2abe6bd299798da6fe99436edb02ce291aa94fa87835d2c5d22b47bddb46558` 527 `SHA256SUMS.txt`
- `7d224617635e9f07e2502de13afceaa7a2d8318a6f14a647e2e4657cd9cf1e0c` 209 `chunk_tail_0_of_2_meta.json`
- `69cea0d09ccf4ddbc562af012857d6968d4225292c3726cc69f0c00a099c1d7f` 227 `chunk_tail_1_of_2_meta.json`
- `7d21d311c0493fff577465c002c6b23dcbf5a63109d7cb63c3feb53e2529b1bf` 1435 `manifest.json`
- `019798567dd754d92343949dcc7412405aeecd5ac7f7ebe6f156e8d2562f23fc` 3779429 `matched_tail_outcomes.csv`
- `ca8b6db2c1c98ce5a2bde1bf0143b8692e9868a83e589c934b9a79e3792cc490` 7205318 `merged_tail.npz`
- `05a54ee9257a013136266f9343bf0c9095c460cefcd6e1a263d68d815646f775` 7830377 `survival.json`
- `609808e1c11f417e6c623f441ec7681c14feadc08b1fe038cb5bcd58e4f2acdb` 2633172 `survival_curve.csv`

### prospective-tail-scoring (folder of 6 .npy decodes exactly to n=12809 cohort; see log)
- `b1b1443afdb6e9e2bf1e78ec5617f36a0568c8b62102023dc2474e196d13efc0` 346 `OUTPUT_MANIFEST.json`
- `38deb3ae094a856980abd86786016a0954e099e15895c9333b29059d37f05ba8` 7156 `prospective_tail_scoring.json`
- `f5fefa13a292ff5b4af86174fc358648bff93e2c678f72deab75b14934a4f3df` 512488 `prospective_matched_scores/combined_scores.npy`
- `61d452c2a68ffb71ef3231936ab38003a2fefce12322159a9c3333e6aca5e78b` 102600 `prospective_matched_scores/event_time_outer.npy`
- `af8cb2aa10fd2e5a38a604a36acf31b4b3f2f90a6765d06da43cba88dad61fb9` 614960 `prospective_matched_scores/event_type.npy`
- `a77a66e7b65ffb0ccd722b6e8e2edd90907c9e1f00a4075b23829d73db84613a` 168 `prospective_matched_scores/fractions.npy`
- `63acabe3937153e43ec8a71ffc01e8c011f839754ecda37bc72fb784e4126461` 102600 `prospective_matched_scores/system_id.npy`
- `353ee343cbdeedc08b0bfb06953e1002da75ba0ee6364e7da2f34b70f0da128a` 102600 `prospective_matched_scores/y_delayed.npy`

### tail-tolernace (note slug typo: tolErnace)
- `b3d1e29b1b538a6521816552b559e353f62c30a818e5fbe7a3d867e0fb5e5986` 2948 `preselected_ids.txt`
- `4d26c6dd876dd7b9f6e5317b20305aa0ccea890f4c60a77e25184d60feb0bc0b` 36219 `tight_tail_500.npz`
- `e7e570c04bae947a86a12be4af6598c7a131fc5f444c04e850364cc450fb2434` 1931 `tolerance_report.json`

### trainingcurve
- `c8bb41355bce009e7eab73bd87dbad20b9ecc1a78a163f36ddb19ca60b53728f` 189 `OUTPUT_MANIFEST (1).json`
- `a55ec950b5978ab1e6b45d9fd51c029b471e61c40184566eccd2910e97dd9126` 97452 `training_size_curve.json`

### v2chunks (no SHA256SUMS/metas shipped — recommended fix)
- `3f7019f718b0df01c8886b09b52b19e2e2f7d5dd30a7b66b55f7bb7b1505f560` 106566309 `chunk_boundary_0_of_1.npz`
- `0093f10a964bc9b83efb5baf83b8b2dc46e9c8a0da2500a15a1c0a8d78743d0c` 18414392 `chunk_boundary_0_of_1_series.pkl`
- `043709a73236da96d7110b88206625ae45d9e0c25736b4e1acfc6f490f5dcae6` 4172085348 `chunk_encounters_0_of_1.npz`
- `715a8659c1519fc6cef30fab03530675e2adcfd1696dd54936fe4534475476d5` 119427841 `chunk_encounters_0_of_1_series.pkl`
- `57dd00dd5be9cb2aaf8d3f81b0d690ff1fb21cb9a85fdfc90fe4ccfb04302e3c` 481117454 `chunk_triples_0_of_2.npz`
- `977408ff0175d09a2ecdb6fec586fe60687a32643c0151a0a303ccb7abd0c5d5` 116139547 `chunk_triples_0_of_2_series.pkl`
- `c31b5ed26ce855ea1861594ec4da4a334866f4d271834a3e4114ad17d727c56e` 481955064 `chunk_triples_1_of_2.npz`
- `fc989bfdfc4bc0d06a19a96f329178b490b737dd94e078d62d297b567a38dcf6` 116205680 `chunk_triples_1_of_2_series.pkl`

## Verdicts (all green unless noted)

1. Manifest §2 mapping 3/3 CONFIRMED by full sha256:
   `187835e0…`→`mergedtriples/merged_triples.npz`,
   `ece95247…`→`3000t-out/v2out/chunk_tail_0_of_2.npz`,
   `5029ad43…`→`3000t-outpart-2/chunk_tail_1_of_2.npz`.
2. §3 chunk-0 test PASSES: chunk0 ejected = 20064 exactly.
   Ledger: chunk0 {ejected 20064, stable 29905, num_err 31, collision 0} = 50000;
   chunk1 {ejected 20015, stable 29948, num_err 36, collision 1} = 50000;
   merged {ejected 40079, stable 59853, num_err 67, collision 1} = 100000. Seeds 42, ~130 min each.
3. `final-audit-expanded/SHA256SUMS.txt`: 23/23 entries match walk. `deeptail_final/SHA256SUMS.txt`: 6/6 match.
   `deeptail_final/manifest.json` files block (bytes+sha) matches walk; its `source` block hashes
   match the three big inputs (`ece95247…`, `5029ad43…`, `187835e0…`). Provenance chain closed.
4. Chunk metas identical across datasets (`7d224617…`, `69cea0d0…` in 3000t-out/part-2/posttail).
5. `merged_tail.npz` (7205318 B) ≈ chunk0+chunk1 (3604219+3603997 B). Consistent merge.
6. `prospective_matched_scores/*.npy` sizes decode exactly (128-B headers) to n=12809:
   3×102600 (12809×8), event_type 614960 (12809×6×8), combined_scores 512488 (12809×5×8), fractions 168 (5×8).
7. `analysis/analysis_final_4core/` is FINAL-era (indices 72+73 zeroed, two features disabled) and
   SUPERSEDES repo `results/corrected_analysis_4core/` (index 73 only). Only `ma01_benchmark.json`
   (`98f8af76…`) and `spike_study.json` (`62c174c5…`) are byte-identical. Same `n_pos`=174138 in
   triples_decision; warned 51659→50821 and median lead 16.777→16.527 shift in the expected
   direction after disabling the second feature. Recommendation: commit Kaggle's 19 files as new
   `results/final_analysis_4core/` (keep corrected-era dir for history); delete one Kaggle subfolder dup.
8. Open issues: `tail-tolernace` slug typo; `OUTPUT_MANIFEST (1).json` dup; 10 Unknown licenses +
    missing descriptions; v1 attribution-growth needs deprecation note; missing checksums/metas on
    `v2chunks/`+`mergedtriples/`; `merged_triples.npz` (1.82 GB) ≈ 1.9× parts sum — owner to confirm
    extra contents; §9 manifest `.npz` reference is stale (real artifact is the 6-file folder);
    §10 partial-AUC + §12 V22/V23 outputs missing everywhere (remaining 5 §16 hashes unmapped).

## Addendum 2026-09-27 — analysis-agent resolutions (recorded, Kaggle fixes in progress)

- **Merged-size question (B):** resolved. `merged_triples.npz` is uncompressed
  `np.savez` (dominant array `feats` 500000x11x79 float32 = 1,738,000,000 bytes);
  production chunks are compressed. The 116 MB series PKLs are separate
  diagnostics, not contained in the merged NPZ. No unexplained bytes.
- **Sklearn version (E1):** BLOCKED, honestly. FINAL runs installed unpinned
  scikit-learn; the version is absent from run logs and must not be guessed.
  Manifest wording: `runtime sklearn version not captured`. Vynatheya pickles
  declare sklearn 1.2.2 (compat warnings under Kaggle runtime). Release env pins
  going forward (`requirements-release.txt`).
- **Δ103/Δ98 (E2):** resolved as cross-run transitions, not ledger discrepancies
  (see `results/final_manifest.json` → `tail_ledger.delta_103_98`).
- **Prospective NPZ (A8):** original container hash
  `3978f8aa7c44716c732d528b6d2e39ebf4c147909ff5cd21e0e2e58b4a96c488`
  recorded as provenance-only; the six public NPYs are canonical. A reconstructed
  NPZ would carry a new hash and must never claim the old one.
- **Nine script hashes (D):** recorded in `results/final_manifest.json` and
  `workflows/final/SCRIPT_REGISTRY.json`; bytes pending receipt.
- **§12 scope:** literature-baseline track = `LITERATURE_BASELINE_VYNATHEYA_4CORE.py`
  + `literature_baseline_results.json` + scores + pinned public model files + manifest.
- **Kaggle cleanup plan:** typo-slug recreation, dup deletions, CC BY-SA 4.0 +
  data cards, v1 deprecation note, tail-layout alignment, v2chunks/mergedtriples
  checksums (no NPZ byte changes), §10/§12 uploads. Owner track; registry notes
  the target state per dataset.

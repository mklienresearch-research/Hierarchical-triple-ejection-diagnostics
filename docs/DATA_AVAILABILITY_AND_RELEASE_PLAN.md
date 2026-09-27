# Data Availability and Release Plan

## During anonymous ApJ review

The anonymous manuscript will not cite author-identifying Kaggle URLs. It will state that a frozen code and derived-results archive is available to editors/reviewers through the submission system or on request. Public GitHub identity and final archival DOI will be inserted only in the accepted/public version, consistent with journal instructions.

Suggested anonymous wording:

> The analysis code, machine-readable derived result tables, and artifact checksums have been frozen for review and are available to the editor and referees through an anonymized archive. The multi-gigabyte simulation products will be deposited in a versioned archival repository upon acceptance. No observational data were used.

## At publication/acceptance

### GitHub

Publish under MIT:

- source package;
- nine final run/post-processing scripts;
- tests and CI;
- small JSON/CSV result tables;
- final figures and manuscript source;
- checksums, schemas, manifests, and download helpers.

Do not commit multi-gigabyte NPZ/PKL products to ordinary Git history.

### Zenodo

Deposit large simulation/data artifacts with DOI:

- production chunks and merged arrays;
- time-series PKLs where included;
- matched deep-tail arrays;
- frozen score/split arrays;
- tolerance-validation NPZ;
- complete manifests/checksums/environment metadata.

Connect the archival release to the GitHub release. Cite the Zenodo DOI in the final Data Availability statement.

Suggested final wording:

> Source code, tests, derived result tables, and figure-generation workflows are available at [GitHub release URL]. The versioned simulation and score archives are available at Zenodo [DOI]. Files are accompanied by SHA-256 manifests and machine-readable schemas.

## Kaggle role

Kaggle datasets are compute/staging artifacts and need not be cited in the paper. Preserve them until Zenodo ingestion and checksum verification are complete. Mark superseded Kaggle artifacts clearly and avoid minting DOI links for typo/superseded slugs.

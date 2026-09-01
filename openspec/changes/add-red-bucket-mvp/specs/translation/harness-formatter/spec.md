## Purpose

The formatter is red-bucket's core value: at fetch time it converts assets stored in one harness's format into the format of the requesting harness, preserving functional behavior, with per-pair rules documented and experimentally verified.

## ADDED Requirements

### Requirement: Fetch-time translation
The system SHALL provide a fetch endpoint that takes a target harness (`codex`, `claude`, `agents`, `openclaw`) and returns the requested asset (or whole bucket) converted from its source harness format to the target harness format, including the target-appropriate file names, directory layout, and metadata schema. Fetching with the target equal to the source harness MUST return content byte-identical to the raw download.

#### Scenario: Claude skill fetched as codex
- **WHEN** a client fetches a skill stored with source harness `claude` specifying target harness `codex`
- **THEN** the response contains the skill re-laid-out per the codex convention with name, description, instructions, and referenced auxiliary files preserved, as defined in `cross-transfer/claude-2-codex.md`

#### Scenario: Identity translation is byte-identical
- **WHEN** a client fetches an asset specifying a target harness equal to the asset's source harness
- **THEN** the returned content is byte-identical to the raw download of that asset

#### Scenario: Whole-bucket fetch
- **WHEN** a client fetches an entire bucket for a target harness
- **THEN** the response is an archive in which every translatable asset is converted and arranged in the target harness's expected directory positions, ready to be unpacked into the user's local harness config

### Requirement: Supported translation pairs declared
The system SHALL expose a capability matrix endpoint declaring, per asset type, which source-to-target harness pairs are supported. Requests for an unsupported pair MUST fail with HTTP 501 and error code `translation_unsupported`, never silently return untranslated content. Phase 1 MUST support at least: `skill` and `instructions` between all four harness styles, and `mcp` between `claude` and `codex`.

#### Scenario: Capability matrix served
- **WHEN** a client requests the translation capability matrix
- **THEN** the response enumerates supported (asset type, source, target) triples consistent with the published cross-transfer docs

#### Scenario: Unsupported pair rejected explicitly
- **WHEN** a client requests a translation pair absent from the matrix
- **THEN** the system responds HTTP 501 with `translation_unsupported` and does not return the untranslated source content

### Requirement: Functional equivalence of translated assets
Translation SHALL preserve the functional behavior of the asset: after translation, the asset installed into the target harness MUST trigger under equivalent conditions and produce equivalent effect as the source asset in the source harness. Information that has no target-side equivalent MUST be preserved in a designated compatibility note within the output rather than silently dropped.

#### Scenario: Migrated skill behaves equivalently
- **WHEN** a benchmark skill is installed in its source harness and its translation is installed in the target harness, and both are exercised with the same task prompt
- **THEN** both harnesses recognize and invoke the skill, and the observable outcome matches per the equivalence checklist in the corresponding cross-transfer doc

#### Scenario: Untranslatable fields preserved as notes
- **WHEN** a source asset contains a field with no equivalent in the target harness
- **THEN** the translated output carries that field in a compatibility-notes section and the fetch response flags the asset with a `lossy: true` marker

### Requirement: Translation rule documents
Each supported source-to-target pair SHALL be documented in `cross-transfer/<src>-2-<dst>.md` covering: both harnesses' formats for skill, plugin, mcp, and subagent content; the field-by-field mapping; the user-facing operations during migration; and the behavior changes a user will observe. Each document MUST be validated by a recorded experiment before its pair is marked supported in the capability matrix.

#### Scenario: Doc exists for every supported pair
- **WHEN** the capability matrix reports a (type, src, dst) triple as supported
- **THEN** `cross-transfer/<src>-2-<dst>.md` exists and contains the mapping table covering that asset type and a link to its experiment record

#### Scenario: Undocumented pair not exposed
- **WHEN** a translation pair has no validated cross-transfer document
- **THEN** the capability matrix reports it unsupported

### Requirement: Deterministic translation
Translation SHALL be deterministic: the same source content and target harness MUST always produce identical output bytes, so fetches are cacheable and diffable.

#### Scenario: Repeated fetch identical
- **WHEN** the same asset at the same commit is fetched twice for the same target harness
- **THEN** both responses are byte-identical

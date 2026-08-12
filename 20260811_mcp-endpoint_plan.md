# Plan: MCP endpoint for the IMAGE orchestrator

Date: 2026-08-11
Branch: `mcp-endpoint`
Status: **IN PROGRESS**

This is the authoritative implementation and handoff document. It incorporates the
initial research, the review of the interrupted implementation, and all decisions made
after that review. A new implementer should be able to continue from this file without
the chat history.

## Goal

Expose a standard Streamable HTTP MCP endpoint at `POST /mcp` beside the existing
`POST /render` endpoint. The MCP server will expose one discoverable tool,
`interpret_graphic`, which accepts a graphic, runs the existing IMAGE pipeline, and
returns only experiences that the client can use:

- Text renderings appear directly as MCP text content.
- Audio renderings are made available through an accessible MCP App when supported.
- Clients without the App receive text, segment/timepoint information, and an audio
  artifact link. Native MCP audio blocks may be added after client testing.
- Renderings that cannot be faithfully represented are dropped.

Primary clients are Claude Code, Claude Cowork, Claude Desktop, and ChatGPT. The primary
users are blind or have low vision, so screen-reader and keyboard behavior is a release
criterion rather than an enhancement.

## Confirmed IMAGE behavior

- The orchestrator is Express 4 and TypeScript. `/render` validates an IMAGE request,
  executes pseudo-preprocessors, preprocessors, and handlers, then returns
  `{request_uuid, timestamp, renderings}`.
- Supported relevant rendering types are:
  - `ca.mcgill.a11y.image.renderer.Text`: `data.text`
  - `ca.mcgill.a11y.image.renderer.SimpleAudio`: `data.audio`
  - `ca.mcgill.a11y.image.renderer.SegmentAudio`: `data.audioFile` plus
    `data.audioInfo: [{name, offset, duration}]`
- SegmentAudio `offset` and `duration` values are seconds. These entries are the
  requested timepoints.
- Graphic IMAGE requests require actual pixel `dimensions: [width, height]`.
- Existing generated audio is normally compressed MP3 and less than two minutes.
- The browser extension presents SegmentAudio with a full-rendering button, one button
  per segment, and a download link.
- `/var/log/IMAGE/<request_uuid>/` is the existing canonical temporary experience
  location when `STORE_IMAGE_DATA=ON`. It contains `request.json` and `response.json`;
  `response.json` contains the complete IMAGE renderings, including base64 audio.
- `/tmp/sc-store` is not an experience-retention location. It is shared scratch storage
  used while SuperCollider creates audio; the handlers delete its WAV, JSON, and MP3
  intermediates after embedding the MP3 in the handler response.
- `orchestrator/clean-cron` removes request directories under `/var/log/IMAGE` after one
  hour unless an `auth` marker exists; marked directories are retained for 60 days.

## Protocol targets

### MCP 2026-07-28

Use the current official MCP v2 server stack rather than hand-rolling modern MCP:

- `@modelcontextprotocol/server@2.0.0` requires Node >=20.
- `@modelcontextprotocol/express@2.0.0` requires Node >=20 and supports Express
  `^4.18.0 || ^5.0.0`; an Express 5 migration is not required.
- Modern requests are stateless and carry protocol version and client capabilities in
  per-request `_meta`.
- Implement `server/discover`, `tools/list`, `tools/call`, `resources/list`, and
  `resources/read` through the SDK and Express adapter.
- Modern results require `resultType`, and cacheable list/resource results require
  `ttlMs` and `cacheScope`.
- Follow the SDK for header/body validation, status codes, JSON-RPC errors, and
  notifications instead of duplicating the specification manually.

### MCP 2025-11-25 fallback

Support the immediately previous protocol revision with a small, isolated compatibility
adapter only if the v2 SDK does not provide it.

The fallback is intentionally **stateless**:

- Answer `initialize` with protocol version `2025-11-25`, stable tool/resource
  capabilities, server identity, and instructions.
- Do not mint `Mcp-Session-Id` and do not retain client capabilities from `initialize`.
- Implement only the required methods for this server: `initialize`,
  `notifications/initialized`, `ping`, `tools/list`, `tools/call`, `resources/list`, and
  `resources/read`.
- Use legacy response shapes and legacy HTTP/error behavior. In particular, do not apply
  2026-specific HTTP status rules indiscriminately to legacy calls.
- The tool list and tool metadata must be deterministic and independent of earlier
  requests.

#### End-user effect of stateless legacy mode

The server cannot remember whether a 2025-11-25 client advertised MCP Apps support during
`initialize`. Therefore:

- Every legacy result must include a portable text/link fallback.
- UI resource metadata is advertised consistently; non-App clients ignore it.
- Results must not depend on capabilities remembered from `initialize`.
- The server cannot optimize away App metadata or artifact metadata for an individual
  legacy client.
- Some older clients may show only the text and artifact link even if they have partial UI
  support. This is accepted for the prototype and must be documented.
- Session-aware capability tailoring may be added later if real client testing shows a
  material benefit.

## Phase 0: Runtime and dependency upgrade

Complete this before MCP implementation.

1. Pin both Docker stages to a supported Node 20 Alpine image instead of floating
   `node:alpine`.
2. Change `.github/workflows/orchestrator.yml` from Node 16 to Node 20. Upgrade the
   checkout/setup-node actions while touching the workflow.
3. Add `engines.node: ">=20"` to `orchestrator/package.json`.
4. Upgrade TypeScript to a stable 5.x release compatible with all dependencies (prefer
   5.9.x for this implementation, not unreviewed TypeScript 7), `@types/node` to Node 20,
   and compatible ESLint/typescript-eslint versions.
5. Keep Express 4, but update to the latest compatible Express 4 security release.
6. Remove `node-fetch` and use Node 20's built-in `fetch`, `Response`, and
   `AbortController`. This avoids the current ESM-only `node-fetch` v3/CommonJS mismatch.
7. Regenerate `package-lock.json` with Node 20 and run `npm audit`.
8. Recheck `ajv`, `dockerode`, `memjs`, `object-hash`, `uuid`, and their type packages for
   Node 20 and TypeScript 5 compatibility. Do not upgrade unrelated behavior without a
   reason.
9. Verify Docker builds on the deployment architecture. Any native image dependency must
   have compatible Alpine/musl packages.

### MCP SDK compatibility spike

Do this before committing dependency choices:

- Prove a minimal `server/discover` and `tools/list` endpoint with
  `@modelcontextprotocol/server@2.0.0` and `@modelcontextprotocol/express@2.0.0` mounted on
  the existing Express 4 app.
- Verify the v2 SDK's actual 2025-11-25 support. If absent, isolate legacy handling behind
  a separate adapter; do not fork or bypass the SDK for modern requests.
- `@modelcontextprotocol/ext-apps@1.7.5` currently peers against the v1
  `@modelcontextprotocol/sdk`, while the modern server packages are v2. Do not install
  incompatible SDK generations blindly. Use v2 server metadata/resources directly and
  either:
  - build the browser App in an isolated workspace with ext-apps, or
  - use only ext-apps browser code proven not to couple to the v1 server, or
  - use a later ext-apps release once its v2 compatibility is confirmed.
- Record the exact resolved versions and the result of this spike in this document.

Dependency audit performed on 2026-08-11:

- Confirmed `@modelcontextprotocol/server@2.0.0`: Node >=20, Zod 4, MCP core 2.0.
- Confirmed `@modelcontextprotocol/express@2.0.0`: Node >=20, Express 4 or 5 peer,
  MCP server v2 peer.
- Confirmed `@modelcontextprotocol/ext-apps@1.7.5`: Node >=20, but v1 MCP SDK peer.
- The existing Docker build reports deprecated lint dependencies and seven audit findings
  before production pruning (four moderate, three high), and five after pruning (four
  moderate, one high). Phase 0 must identify and resolve or explicitly document each
  finding rather than applying `npm audit fix --force` blindly.

Step 2 verification performed on 2026-08-11:

- Both Docker stages use the pinned `node:20.19.2-alpine3.21` image. The orchestrator
  workflow uses Node 20, `actions/checkout@v4`, and `actions/setup-node@v4`.
- Resolved direct versions are Express `4.22.2`, AJV `8.20.0`, UUID `11.1.1`, TypeScript
  `5.9.3`, ESLint `8.57.1`, typescript-eslint `8.67.0`, Vitest `3.2.7`, and Supertest
  `7.1.3`. `dockerode` `3.3.5`, `memjs` `1.3.2`, and `object-hash` `2.2.0` were retained
  because they remain compatible with Node 20 and require no behavior change.
- Removed `node-fetch`; the pipeline uses Node 20's built-in `fetch`, `Response`, and
  `AbortController`. UUID was updated from v8 to v11.1.1 to resolve its direct audit
  finding; its CommonJS export supports the current runtime/import style.
- `npm audit fix` applied only non-breaking transitive updates. The subsequent audit
  reports zero vulnerabilities; no `--force` upgrade was used.
- The Docker builder runs `npm test` before producing the production image, so the
  regression suite executes under the pinned Node 20 Alpine runtime as well as in CI.

## Shared IMAGE pipeline

`/render` and `/mcp` must call the same extracted pipeline function. The extraction must
remain behavior-equivalent for `/render`:

- Request validation remains at the endpoint boundary.
- Response validation errors are copied immediately so concurrent AJV calls cannot
  overwrite them.
- `/render` sends its response before waiting for optional request/response persistence,
  matching the original behavior.
- Request timing and error logging remain equivalent and are not duplicated.
- Persistence remains an endpoint concern, not hidden inside the core pipeline.

## Tool definition

Expose one tool:

- Name: `interpret_graphic`
- Title: `IMAGE graphic interpreter (photos, images, screenshots, and charts)`
- Annotation hints: read-only, non-destructive, non-idempotent, open-world.
- The description must be factual and concise. It should explain that the tool creates
  accessible text and audio interpretations for blind and low-vision users and can be
  used for an image supplied directly or obtained from another connector. Avoid wording
  that orders the model to upload private data automatically.
- Advertise a same-origin IMAGE icon and the audio UI resource.

### Input sources

The schema must require exactly one supported source:

1. `graphic`: a base64 image data URL. Validate base64 strictly and verify the MIME type
   using decoded magic bytes.
2. `file`: the ChatGPT file object supported through `_meta["openai/fileParams"]`, using
   the current ChatGPT-documented fields such as `download_url`, `file_id`, `mime_type`,
   and `file_name`.

Do not add a general arbitrary `image_url` parameter in the prototype. It expands SSRF
scope. Connector workflows should use a data URL when the host can transfer bytes. A
future production version may add a controlled URL source with full outbound-fetch
protection.

Other optional inputs:

- `language`: BCP 47/IMAGE-compatible language, default `en`.
- `context`: bounded surrounding context.
- `url`: bounded source-page identifier passed to IMAGE as metadata only; the server
  must not fetch it.

The adapter synthesizes the IMAGE request with a UUID, timestamp, context, capabilities,
and these renderer IDs only:

- `ca.mcgill.a11y.image.renderer.Text`
- `ca.mcgill.a11y.image.renderer.SimpleAudio`
- `ca.mcgill.a11y.image.renderer.SegmentAudio`

## Image validation and dimensions

Do not implement a custom byte-header dimension sniffer.

Use a mature image decoder, with `sharp` as the first candidate, to:

- Decode and validate the actual image rather than trusting the declared MIME type.
- Apply orientation metadata.
- Reject unsupported/active formats for the prototype.
- Enforce bounded dimensions, total pixels, frames, and decoded bytes.
- Produce a normalized raster JPEG or PNG and its accurate dimensions before the IMAGE
  pipeline fans the data out to services.

Before adopting `sharp`, verify its Node 20 Alpine/musl and deployment-architecture
support in Docker and CI. If it is not viable, choose another mature decoder with these
properties; do not fall back to an untested custom JPEG/WebP parser.

## Attachment and email behavior

Direct chat attachments are host-specific, not a core MCP guarantee.

- ChatGPT should use its documented file-parameter extension.
- Claude Code/Cowork may be able to read local files, but successful transfer to a remote
  MCP tool must be demonstrated.
- Claude Desktop chat attachments must be tested; do not assume the model receives raw
  bytes suitable for a tool argument.

The scenario "get the photo in the email this morning from Jane in my inbox, and give me
an audio rendering" is conditional:

- It works only if the email connector exposes attachment bytes in a transferable form.
- Embedded email images may not be exposed; Claude Gmail currently has this limitation.
- Test Gmail and Outlook attachments separately and document the exact behavior.
- The prototype documentation must explain this limitation and must not promise universal
  cross-MCP binary transfer.
- Until production privacy/auth controls exist, demonstrate this workflow only with
  synthetic or non-sensitive test mailbox data.

## Rendering conversion

### Text

Return every IMAGE Text rendering as MCP text content so it appears directly in the
conversation and remains available to screen readers.

### Audio artifacts

Do not put normal two-minute MP3 files into the initial MCP JSON result. Even compressed
audio usually exceeds documented App hydration limits after base64 expansion.

For each audio rendering:

1. Parse the existing IMAGE MP3 data URL.
2. Write the decoded MP3 under the same existing request directory as the rest of the
   experience, for example:
   `/var/log/IMAGE/<request_uuid>/mcp-audio/<random-token>.mp3`.
   The MCP artifact writer must create this request directory even when
   `STORE_IMAGE_DATA` is off; in that case the directory may contain only MCP artifacts
   and their minimal metadata. Do not use `/tmp/sc-store`, because it is handler scratch
   space and its files are deleted immediately.
3. The random token must be unguessable and path-safe.
4. Return compact metadata: artifact URL/resource link, MIME type, byte length,
   description, and SegmentAudio timepoints.
5. Serve the artifact from a same-service HTTPS endpoint with MP3 content type and Range
   request support so native controls and seeking work.
6. Do not log the complete artifact URL/token.

The existing cron then removes the whole request directory and audio artifacts after one
hour. Documentation must note that if the existing `/authenticate/:uuid/:check` flow adds
an `auth` marker to the same directory, the directory and artifacts follow the existing
60-day retention instead.

Native MCP `AudioContent` blocks are deferred until target-client tests establish useful
codec and size behavior. Non-App clients receive text, a segment list with timestamps,
and the artifact/resource link.

### Dropped renderings

Drop haptic, tactile, SVG-layer, and unknown rendering types. Log their type IDs and place
compact diagnostic information in vendor-prefixed result metadata; do not expose unusable
payloads to the user.

## MCP App

Register an MCP App UI resource such as `ui://image/audio-experience` with MIME type
`text/html;profile=mcp-app`.

MCP App association is normally declared on the tool before the result is known, so the
host may instantiate the App even when IMAGE produces no audio. If the SDK/spec version
supports reliable result-time UI selection, use it so the App is shown only for audio.
Otherwise, the App must handle all states and always have a non-zero accessible layout:

- Loading
- Simple audio
- Segmented audio
- Mixed text and audio
- Text-only: announce that no audio rendering was produced and that text appears in the
  conversation; also render the text in the App
- No rendering
- Tool error
- Cancelled execution
- Missing or expired audio artifact

For audio, mirror the browser extension:

- A full-rendering play/pause control.
- One native button per timepoint/segment.
- A native audio element or another streaming approach that does not decode an entire MP3
  into PCM unless testing proves that safe.
- Segment seeking/stopping based on `offset` and `duration`.
- A download link when supported.
- IMAGE logo and the exact text: "Brought to you by the McGill IMAGE project. Click here
  for more information." Make the final sentence a link to
  `https://image.a11y.mcgill.ca`, using `ui/open-link` when required by the host.

### Accessibility requirements

- Semantic headings, links, native buttons, and audio controls.
- Keyboard support without custom key traps.
- `aria-pressed` for play/pause and a clear Stop behavior.
- Focus indicators, logical focus order, and minimum 44 by 44 CSS pixel touch targets.
- A polite status region for state changes; alert errors without announcing continuous
  time updates.
- Host theme, locale, safe-area, size, and context-change support with robust fallbacks.
- Correct document language and right-to-left handling where applicable.
- Forced-colors/high-contrast support, reduced motion, 200% and 400% zoom, and a usable
  320 px layout without nested scrolling.
- Treat segment names and text as untrusted text; never insert them as HTML.
- Handle `ui/notifications/tool-cancelled` and `ui/resource-teardown`, stopping and
  releasing media resources.

## Prototype security and privacy limitations

Production hardening is intentionally deferred, but the prototype documentation must
prominently state:

- The endpoint is for demonstration, not production or sensitive/private images.
- When `IMAGE_MCP_TOKEN` is unset, the endpoint is publicly callable like `/render` and
  can consume expensive compute.
- A fixed bearer token is a deployment convenience, not broadly interoperable MCP OAuth.
- OAuth, comprehensive rate limiting, per-user quotas, queue/concurrency limits, artifact
  authorization, complete Origin policy, and hardened outbound fetching are future work.
- Do not use real private inbox images for the email demonstration.
- `STORE_IMAGE_DATA`, cache behavior, the one-hour cron cleanup, and the possible 60-day
  authenticated retention must be documented.

Even for the prototype, retain basic safe behavior: no arbitrary URL fetching, strict
path handling, bounded request/image/audio sizes, no credential logging, and rejection of
malformed inputs.

## Documentation deliverables

Create `orchestrator/MCP.md`, linked from both `orchestrator/README.md` and the root
`README.md`, covering:

- Endpoint and supported protocol revisions.
- `interpret_graphic` inputs and outputs.
- Client setup for Claude Code, Claude Desktop/Cowork, and ChatGPT, clearly separating
  verified from unverified behavior.
- Stateless legacy effects described above.
- Text, App, artifact-link, and dropped-rendering behavior.
- Artifact storage and cron retention.
- Prototype security/privacy warning.
- Attachment limitations and conditional email workflow.
- An attached-photo example prompt.
- A Jane-email example prompt explicitly labeled conditional and for demo data.
- Modern discovery and tool-call examples plus legacy initialize examples.

## Tests

Tests are required, not optional. Add a test runner compatible with Node 20 and TypeScript
5 (Vitest is a reasonable first choice) and wire it into CI.

### Pipeline regression tests

- Existing `/render` success and schema failure behavior.
- Serial and parallel preprocessor paths.
- Cyclic dependency fallback.
- Handler filtering and empty results.
- Request/response persistence timing: response is sent before storage completes.
- Concurrent AJV failures do not exchange error details.

### MCP protocol tests

- Modern discovery, tools, resources, result types, cache fields, required metadata, and
  header validation through the official SDK.
- Legacy initialize, initialized notification, ping, tools/resources, legacy errors, and
  no state leakage between concurrent clients.
- Malformed JSON-RPC, notifications, unknown methods/tools, invalid parameters, and size
  boundaries.
- Stable tool metadata independent of legacy initialize capabilities.

### Input and conversion tests

- Valid JPEG/PNG, orientation, malformed/truncated input, MIME mismatch, invalid base64,
  unsupported formats, oversized pixels/frames, and decoder limits.
- ChatGPT file object handling with mocked temporary downloads.
- Text-only, SimpleAudio, SegmentAudio, mixed, empty, malformed, and dropped renderings.
- Artifact creation under the request directory, random/path-safe names, Range requests,
  missing/expired files, MIME, byte limits, and cron-compatible placement.

### App and accessibility tests

- Test with the MCP Apps reference/basic host and target-client developer tooling.
- Automated browser tests for every App state.
- Axe checks plus keyboard-specific assertions.
- Manual NVDA and VoiceOver acceptance, forced colors, dark mode, zoom, reduced motion,
  narrow/mobile layout, playback, seeking, segment navigation, and expired artifacts.

### Client acceptance matrix

Manually verify and document:

- Claude Code with a local image.
- Cowork with a local file.
- Claude Desktop attachment and MCP App.
- ChatGPT attachment using file parameters and MCP App.
- Gmail embedded image (expected limitation).
- Gmail and Outlook file attachments with synthetic data.

## Ordered implementation steps

Commit each completed and verified implementation step before starting the next step. Keep
the implementation tracker and handoff notes current in the same commit.

1. Complete and verify the interrupted shared-pipeline extraction.
2. Upgrade Node, TypeScript, lint tooling, Express 4 patch level, CI, and Docker; remove
   `node-fetch`; add regression tests.
3. Run and document the MCP v2/Express/ext-apps compatibility spike.
4. Implement modern MCP through the official v2 SDK.
5. Implement the stateless 2025-11-25 compatibility adapter if required.
6. Add the mature image decoder and input-source adapter, including ChatGPT file params.
7. Implement rendering conversion and request-directory audio artifacts.
8. Implement artifact/resource serving with Range support.
9. Build the accessible multi-state MCP App.
10. Add complete protocol, conversion, artifact, App, and accessibility tests.
11. Write `orchestrator/MCP.md` and README links.
12. Run Docker, conformance, target-client, and screen-reader verification.

## Current branch state and handoff

Branch: `mcp-endpoint`

At the time of this revision, all changes are uncommitted. The interrupted work extracted
the existing pipeline into new modules:

- New `orchestrator/src/ajv.ts`
- New `orchestrator/src/pipeline.ts`
- New `orchestrator/src/types.ts`
- Modified `orchestrator/src/server.ts`
- Modified ServiceInfo imports in `orchestrator/src/docker.ts` and
  `orchestrator/src/graph.ts`

No MCP endpoint/module has been implemented. Do not assume an `orchestrator/src/mcp/`
directory exists.

### Implementation tracker

| Step | Status | Notes |
|---|---|---|
| 1. Shared pipeline extraction | completed | Typecheck passed with schemas linked, ESLint had 0 errors (17 existing/moved warnings), Docker image built, and `/health` passed in a container. Behavioral regression tests are part of step 2. |
| 2. Node/toolchain upgrade + pipeline tests | completed | Node 20/TypeScript 5.9/tooling upgrade, built-in fetch, CI and Docker updates, and eight pipeline/`/render` regression tests completed. `npm audit` is clean. |
| 3. MCP SDK compatibility spike | pending | Resolve v2 server vs ext-apps v1 peer skew. |
| 4. Modern MCP endpoint | pending | Official v2 SDK/Express adapter. |
| 5. Stateless legacy fallback | pending | No sessions or retained initialize capabilities. |
| 6. Image/file inputs | pending | Mature decoder + ChatGPT file params. |
| 7. Conversion + audio artifacts | pending | Store beneath request directory for cron cleanup. |
| 8. Accessible MCP App | pending | Prefer audio-only instantiation; otherwise render all states. |
| 9. Documentation | pending | Include prototype and client limitations. |
| 10. Full verification | pending | Protocol, Docker, clients, NVDA, VoiceOver. |

### Last completed work (2026-08-11)

The shared pipeline extraction was repaired after review:

- Removed the premature import/registration of a nonexistent MCP module, so the branch
  builds before MCP work starts.
- Kept request/response persistence outside `runPipeline` and preserved the original
  behavior of sending `/render` responses before awaiting filesystem storage.
- Copied shared AJV errors synchronously before another request can overwrite them.
- Removed duplicate pipeline-level failure logging.
- Verified `npx tsc --noEmit` using the same schema layout as CI.
- Verified ESLint with no errors; warnings remain from existing/moved permissive types and
  non-null assertions.
- Built `orchestrator/Dockerfile` successfully and started the resulting container; the
  `/health` endpoint returned success.

No MCP endpoint, SDK dependency, image decoder, artifact route, App, or MCP documentation
has been implemented. Steps 1 and 2 are complete; the next implementer should start at
ordered step 3 and must keep this file updated after each completed/verified step.

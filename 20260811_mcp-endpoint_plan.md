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

Step 3 compatibility spike performed on 2026-08-11:

- Resolved packages are `@modelcontextprotocol/server@2.0.0`,
  `@modelcontextprotocol/express@2.0.0`, and `@modelcontextprotocol/node@2.0.0`, with
  `@modelcontextprotocol/core@2.0.0` and Zod `4.4.3`. All require Node 20 or later.
- The Express package supplies official Express security/auth middleware, but not an MCP
  route dispatcher. The supported Express 4 composition is the official v2
  `createMcpHandler` from the server package adapted with the official v2 Node
  `toNodeHandler`, passing `req.body` after `express.json()` parsing.
- `orchestrator/test/mcp-sdk-spike.test.ts` proves this composition handles modern
  `server/discover` and `tools/list`. Modern requests require the per-request `_meta`
  envelope and a matching `Mcp-Method` header. The SDK emits `resultType: "complete"`
  and the required cache fields (`ttlMs: 0`, `cacheScope: "private"`) for those results.
- The v2 handler's built-in legacy path was verified with `initialize` and `tools/list`
  for `2025-11-25`. It is stateless: each request uses a new server/transport, does not
  emit `Mcp-Session-Id`, and returns legacy result shapes in SDK-generated SSE frames.
  Therefore Step 5 does not require a custom compatibility adapter; Step 4 must retain
  the SDK default legacy fallback rather than setting `legacy: "reject"`.
- `@modelcontextprotocol/ext-apps@1.7.5` remains excluded. Its only available release
  peers with `@modelcontextprotocol/sdk` v1, which must not be installed beside v2.
  Step 9 must use v2 metadata/resources directly or put any future App dependency in an
  isolated workspace after v2 compatibility is demonstrated.
- `@modelcontextprotocol/node` v2 resolves `@hono/node-server` v1, which has a moderate
  path-traversal advisory. The tested package override selects `@hono/node-server@2.1.0`;
  the complete test suite passes and `npm audit` reports zero vulnerabilities.

Step 4 modern endpoint performed on 2026-08-11:

- `POST /mcp` is mounted on the existing Express application using the verified official
  v2 `createMcpHandler`/`toNodeHandler` composition. It retains the SDK's default
  stateless legacy fallback.
- The server registers the final `interpret_graphic` tool identity, annotations, exactly-one
  source schema, and the `ui://image/audio-experience` UI resource. Its execution returns a
  temporary tool error until Step 6 supplies strict image/file input handling; the resource
  serves a minimal placeholder until Step 9 builds the accessible App.
- `IMAGE_MCP_TOKEN`, when set, requires a fixed Bearer token for `/mcp`. It is intentionally
  only the documented prototype convenience mechanism, not OAuth.
- Endpoint tests verify modern `tools/list`, `resources/list`, and optional token enforcement
  through the production Express app. Resource-read header validation is part of Step 10.

Step 6 image/file inputs performed on 2026-08-11:

- Added `sharp@0.35.3` (Node >=20.9 with Linux musl prebuilds) to decode JPEG, PNG, and WebP
  rather than trusting client MIME data. Input is rotated and normalized to bounded JPEG bytes
  with accurate dimensions before it reaches the shared IMAGE pipeline.
- Data URLs are strict base64 and accept only JPEG, PNG, or WebP. Inputs are limited by decoded
  bytes, pixels, frames, normalized size, language/context/URL bounds, and active or multi-frame
  formats are rejected.
- ChatGPT file objects use only `file.download_url`; downloads require HTTPS, have an abortable
  timeout and byte limits, and are decoded by the same path. General image URLs remain unsupported.
- The tool now synthesizes a UUID IMAGE request and runs the shared pipeline. Until Step 7, it
  exposes only Text renderings directly and reports no text interpretation when IMAGE returns audio only.

Deployment correction performed on 2026-08-12:

- Restored the production TypeScript source root to `src`. Including `test` in the production
  compiler configuration emitted `dist/src/server.js`, while the image entrypoint correctly
  expects `dist/server.js`. Tests remain outside the production output; the Docker builder still
  runs them before compilation.

Step 7 rendering conversion and audio artifacts performed on 2026-08-12:

- Text renderings are returned directly as MCP text content. SimpleAudio and SegmentAudio MP3
  data URLs are strictly decoded and written as mode-0600 artifacts below
  `/var/log/IMAGE/<request_uuid>/mcp-audio/` with random base64url tokens.
- Tool results now include a text/link fallback and compact vendor metadata for each audio
  artifact: MIME type, bytes, artifact path, description, and validated SegmentAudio timepoints.
  Audio base64 is never placed in the MCP result.
- Invalid audio and unsupported rendering types are dropped; type IDs are reported in compact
  vendor metadata. Step 8 will expose the emitted artifact paths through an HTTP route with
  Range support.

Step 8 artifact serving performed on 2026-08-12:

- `GET /mcp/audio/<request_uuid>/<random-token>.mp3` serves only UUID-v4 request paths and
  32-byte base64url tokens from the request directory. It supplies `audio/mpeg`, byte Range
  support, and 404 for malformed, missing, or expired artifacts without disclosing paths.
- Artifact links are absolute and same-origin when the request reaches the service through a
  reverse proxy. A prefix-stripping deployment must set `X-Forwarded-Prefix`; Unicorn's nginx
  `/mcp` location needs `proxy_set_header X-Forwarded-Prefix /image;`, producing public links
  beneath `https://unicorn.cim.mcgill.ca/image/mcp/audio/...`.
- Tests verify partial MP3 responses, Range headers, invalid paths, and missing artifacts.

Step 9 accessible MCP App performed on 2026-08-12:

- Replaced the placeholder audio resource with an inline standalone MCP App. It listens for the
  standard `ui/notifications/tool-result` bridge notification, treats all result data as text,
  and uses native audio controls plus one native button per validated segment.
- The resource reports polite status changes, stops playback on teardown/cancellation, provides
  a download link, uses focus-visible controls with 44px targets, and includes the required
  McGill IMAGE attribution/link.
- The tool now advertises both standard nested `_meta.ui.resourceUri` and ChatGPT's
  `_meta["openai/outputTemplate"]` compatibility alias. Results include compact
  `structuredContent` so the App can render audio without parsing the conversation text.
- Correct the Unicorn nginx `/mcp` proxy header to preserve Traefik's HTTPS protocol:
  `proxy_set_header X-Forwarded-Proto $http_x_forwarded_proto;`. Do not use `$scheme`, because
  nginx receives Traefik traffic over HTTP and would generate unusable `http` artifact links.
- The first deployed App used a cached URI and omitted the required `ui/initialize` lifecycle
  handshake. The corrected version uses `ui://image/audio-experience-v2`, completes
  `ui/initialize` then `ui/notifications/initialized`, and therefore allows hosts to send the
  tool-result notification. Set `IMAGE_MCP_PUBLIC_ORIGIN=https://unicorn.cim.mcgill.ca` so the
  App CSP permits its externally hosted MP3 artifacts.
- ChatGPT's current UI runtime may hydrate `window.openai.toolOutput` instead of delivering the
  portable tool-result bridge notification. The third, cache-busting resource URI
  `ui://image/audio-experience-v3` supports both paths and listens for ChatGPT's
  `openai:set_globals` event; it also includes ChatGPT's widget-CSP compatibility metadata.
  The App continues to use the portable MCP initialization and tool-result notification path for
  non-ChatGPT hosts.
- Verification on 2026-08-12: `npm test` passes 20 tests, `npm run build` passes (with 16
  pre-existing lint warnings), `npm audit --omit=dev` reports zero vulnerabilities, and the
  pinned Node 20 Alpine Docker image builds successfully.
- ChatGPT requires an `outputSchema` for tools returning `structuredContent`. The fourth resource
  URI, `ui://image/audio-experience-v4`, declares the exact audio/text result schema. The App also
  reads `toolResponseMetadata.mcp_tool_result.structuredContent`, ChatGPT's canonical full result
  envelope, if its compatibility `toolOutput` global is absent.
- Verification on 2026-08-12: the `tools/list` integration assertion confirms the emitted
  descriptor contains the schema and App visibility. `npm test` passes 20 tests, `npm run build`
  passes with the existing 16 lint warnings, `npm audit --omit=dev` is clean, and the pinned Node
  20 Alpine Docker image builds successfully.
- ChatGPT's MCP Apps resource fetch currently omits the MCP v2 `Mcp-Name` header required by the
  v2 SDK when it sends `resources/read`. The `/mcp` adapter derives that header only from the same
  request's `params.uri`, allowing the SDK to validate and serve the declared `ui://` resource.
- The documented ChatGPT resource convention uses a `.html` path. The App now advertises the
  cache-busting `ui://image/audio-experience-v5.html` URI. The MCP adapter logs each resource-read
  URI and protocol headers so any remaining host incompatibility is observable from orchestrator
  logs without exposing tool inputs or outputs.

Steps 8-10 completion verification performed on 2026-08-12:

- Artifact serving now preserves proper 416 responses for unsatisfiable ranges and avoids logging
  error objects that can contain artifact filesystem paths or secret tokens. Tests cover complete,
  fixed, open-ended, suffix, and unsatisfiable requests plus UUID/token rejection.
- The cache-busting `ui://image/audio-experience-v7.html` App renders text-only and mixed results,
  every returned audio experience, explicit Stop controls, an IMAGE wordmark, tool errors,
  cancellation, and expired artifacts. It releases media on cancellation/teardown and applies host
  locale and text direction when supplied.
- Conversion rejects non-finite timepoints and mismatched data-URL MIME declarations. Dropped
  rendering type IDs are logged without payloads or artifact URLs.
- The suite contains 35 tests across protocol behavior, input normalization and downloads,
  rendering conversion, artifact files and byte ranges, executable App states, and Axe
  accessibility checks. `npm test`, `npm run build`, and `npm audit --omit=dev` pass; build lint has
  the same 16 pre-existing warnings. Manual target-client, screen-reader, zoom, and forced-colors
  acceptance remains ordered Step 12 rather than an automated Step 10 claim.
- ChatGPT `+` attachments initially failed because the tool descriptor omitted
  `_meta["openai/fileParams"]` and did not require the documented `download_url` and `file_id`
  fields. The descriptor now declares `file` as a file parameter with the exact OpenAI file-object
  schema, allowing ChatGPT to replace its local attachment reference with a temporary HTTPS URL.

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
codec and size behavior. Audio artifact links and segment metadata remain in structured
App data and are not duplicated as conversation text.

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
- Text-only: render the text in the App as well as the conversation
- No rendering
- Tool error
- Cancelled execution
- Missing or expired audio artifact

For audio, mirror the browser extension:

- Native audio controls for full-rendering playback.
- One native button per timepoint/segment.
- A native audio element or another streaming approach that does not decode an entire MP3
  into PCM unless testing proves that safe.
- Segment seeking/stopping based on `offset` and `duration`.
- A download link when supported.
- Do not display internal audio rendering descriptions such as "Rich audio description".
- The bundled `orchestrator/src/image_logo.png` embedded in the App as a PNG data URL, and the text "Brought
  to you by the McGill IMAGE project.", with "McGill IMAGE project" linked to
  `https://image.a11y.mcgill.ca` using `ui/open-link` when required by the host.

### Accessibility requirements

- Semantic headings, links, native buttons, and audio controls.
- Keyboard support without custom key traps.
- Accessible native playback controls and clear segment behavior.
- Focus indicators, logical focus order, and minimum 44 by 44 CSS pixel touch targets.
- A polite, visually hidden status region for successful results, using "IMAGE
  experiences ready above"; alert errors without announcing continuous time updates.
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
| 3. MCP SDK compatibility spike | completed | Official v2 server/Express/Node composition proven on Express 4; ext-apps v1 peer skew remains isolated. |
| 4. Modern MCP endpoint | completed | `/mcp`, tool/resource discovery, optional fixed-token auth, and SDK-managed modern/legacy behavior are in place. |
| 5. Stateless legacy fallback | not required | v2's verified built-in stateless 2025-11-25 fallback meets this requirement. |
| 6. Image/file inputs | completed | Sharp-backed validation/normalization, constrained ChatGPT download support, and shared-pipeline request synthesis are in place. |
| 7. Conversion + audio artifacts | completed | Text conversion, compact audio metadata, random request-directory MP3 artifacts, timepoints, and dropped-rendering diagnostics are in place. |
| 8. Artifact serving | completed | Same-service MP3 route, constrained paths, Range support, and reverse-proxy-aware public links are in place. |
| 9. Accessible MCP App | completed | ChatGPT/MCP Apps metadata, structured result payload, native audio/segment controls, and accessible App lifecycle behavior are in place. |
| 10. Automated verification | completed | 35 protocol, input/conversion, artifact, executable App-state, and Axe tests pass. Manual client and assistive-technology acceptance remains Step 12. |
| 11. Documentation | pending | Include prototype and client limitations. |
| 12. Deployment/client verification | pending | Docker, target clients, NVDA, VoiceOver, zoom, and forced-colors acceptance. |

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

No production MCP endpoint, image decoder, artifact route, App, or MCP documentation has
been implemented. Steps 1 through 3 are complete; the next implementer should start at
ordered step 4 and must keep this file updated after each completed/verified step.

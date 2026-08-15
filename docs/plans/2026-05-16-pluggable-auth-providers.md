# Brief: Pluggable identity providers for PAL (and a case for MCP upstream)

**Status:** proposed, not yet scheduled
**Author:** session analysis 2026-05-16
**Estimated effort:**
  - PAL-level interim: ~6-8 hours
  - Upstream proposal: open-ended (community/spec work)
**Related:** `src/pal/oauth.py` (current ~300-line OAuth 2.1 + PKCE implementation)

> Note: this brief differs in shape from the other two in `docs/plans/`.
> They propose clean internal refactors. This one proposes both a
> PAL-level change *and* a position to take with the upstream MCP spec.
> The PAL-level work is concrete and shippable; the upstream piece is
> a longer-running design conversation.

## Problem

MCP delegates authentication to each server, forcing per-server
reinvention of identity validation. PAL is the in-house example:

- `src/pal/oauth.py` is a complete OAuth 2.1 + PKCE authorization
  server: dynamic client registration, authorization-code flow,
  code-verifier exchange, HMAC-SHA256 token signing, IP-CIDR
  allowlisting as a bypass.
- This is hundreds of lines of security-critical code for what is
  fundamentally a **single-user personal layer**.
- Worse, the implementation ignores identity that already exists at
  lower layers — Tailscale's network-layer identity, mTLS client
  certs, reverse-proxy headers from Cloudflare Access / Pomerium /
  oauth2-proxy. PAL re-authenticates a user the transport already
  authenticated.

The same problem recurs in every MCP server that needs auth. The cost
is paid N times across the ecosystem, with the security risk that
implies (N copies of cryptographic code, N times the bug surface, low
per-server motivation to patch).

## Goal

Define a **pluggable identity model** where:

1. Identity sources (OAuth, mTLS, transport-derived, API key, JWT
   from a reverse proxy) implement a common interface.
2. Servers compose the providers they accept.
3. The protocol carries validated identity downstream, not raw
   credentials.
4. PAL's `oauth.py` shrinks to one provider implementation among
   several, instead of being the entire auth subsystem.

## Proposed design (three layers)

### Layer 1: Protocol envelope (upstream MCP)

Add to the MCP spec a standard request-level identity carrier:

```
mcp-identity: <provider>:<token>
```

…plus a defined `Identity` shape that providers return after
validation:

```json
{
  "provider": "tailscale",
  "subject": "alice@tailnet",
  "claims": { ... },
  "expires_at": "2026-05-16T07:00:00Z"
}
```

The spec defines **where identity lives and what shape it has after
validation**. It does *not* mandate any specific provider.

### Layer 2: Capability negotiation (upstream MCP)

Servers declare accepted providers in their capability advertisement:

```json
"authProviders": ["tailscale", "mtls", "oauth2"]
```

Clients pick one they can satisfy and present a token via the
standard header. No protocol-level OAuth dance — OAuth is just *one*
of N provider options.

### Layer 3: Reference libraries (community / ecosystem)

Separate packages, each implementing the same interface:

```python
class IdentityProvider(Protocol):
    name: str
    def verify(self, token: str, request: Request) -> Identity | None: ...
```

Initial set: `mcp-auth-tailscale`, `mcp-auth-mtls`, `mcp-auth-oauth`,
`mcp-auth-apikey`, `mcp-auth-jwt` (for reverse-proxy injected
identities like Cloudflare Access).

Server authors compose them at startup:

```python
mcp = FastMCP("pal-server", auth_providers=[
    TailscaleProvider(),       # try transport identity first
    OAuthProvider(secret=...),  # fall back to OAuth for external clients
])
```

## PAL-level interim (shippable without waiting for upstream)

Before the upstream spec lands (which may take quarters), PAL can
adopt the pattern *internally* and benefit immediately:

1. Define `pal/auth/providers.py` with an `IdentityProvider`
   interface mirroring the proposed upstream shape.
2. Implement initial providers:
   - `TailscaleProvider` — reads `Tailscale-User-Login` header.
   - `OAuthProvider` — wraps the existing `oauth.py` logic.
   - `APIKeyProvider` — checks against a configured key list.
   - `NetworkProvider` — replaces today's `PAL_OAUTH_ALLOWED_NETWORKS`
     bypass with an explicit identity source returning a
     `network:trusted` subject.
3. Wire `FastMCP` construction in `src/pal/tools/registry.py` to
   accept the composed provider chain.
4. Expose the resolved `Identity` to tool handlers via the request
   context (e.g., `ctx.identity`).

When upstream lands, swap PAL's internal interface for the standard
one — the rest of the code is unchanged.

### What gets deleted (eventually)

- The bulk of `src/pal/oauth.py` (kept only as `OAuthProvider`).
- The `PAL_OAUTH_ALLOWED_NETWORKS` env var (replaced by
  `NetworkProvider` composition).
- Any ad-hoc identity-discovery logic scattered through tool
  handlers.

### What stays unchanged

- Tool registration and dispatch.
- Per-tool authorization (what a given identity is allowed to do —
  this stays server business logic, see Out of Scope).
- Existing OAuth clients (they continue to authenticate via
  `OAuthProvider`).

## Trade-offs / open questions

1. **Authorization vs authentication.** This proposal addresses
   *who you are*, not *what you can do*. Per-tool ACLs remain a
   server concern. Most MCP servers don't have complex
   authorization needs, but multi-tenant servers will eventually
   want a policy layer. v2 problem.
2. **Backwards compatibility.** Existing OAuth clients must
   continue to work without code changes. The OAuth flow becomes
   one provider; clients are unaware of the change.
3. **Upstream timeline is uncertain.** The PAL-level interim is
   designed to be valuable on its own — if upstream never
   converges on this design, PAL still wins by deleting bespoke
   OAuth code and gaining Tailscale/mTLS support.
4. **Who maintains reference providers?** Realistic answer: a
   community-driven repo of `mcp-auth-*` packages, mirroring the
   shape of `mcp-server-*` packages. Initial implementations come
   from servers like PAL extracting their internal versions.
5. **Tailscale headers are trust-on-first-deploy.** A
   `TailscaleProvider` must verify it's actually behind a Tailscale
   subnet (not a spoofed header from the open internet). Document
   the deployment constraint clearly; consider a `verify_remote_ip`
   option.
6. **Identity claims schema** is not standardized in v1 — providers
   return their native claims. Cross-provider claim normalization
   (e.g., "give me a stable user_id regardless of provider") is a
   follow-up.

## Verification approach

### PAL-level interim
1. Unit tests per provider in `tests/test_auth_providers.py`:
   - `TailscaleProvider.verify(...)` accepts valid `Tailscale-User-Login`
     header, rejects when header is absent.
   - `OAuthProvider.verify(...)` accepts a token signed by the
     server's secret, rejects mismatched signatures and expired
     tokens.
   - `APIKeyProvider.verify(...)` matches configured keys.
   - `NetworkProvider.verify(...)` returns `Identity` for IPs in
     allowed CIDR list, `None` otherwise.
2. Integration test: same tool call, three providers in sequence,
   first-match wins.
3. Migration test: existing OAuth client authenticates with no
   client-side change after the refactor.

### Upstream proposal
1. Working reference implementation in PAL (validates the design
   under real use).
2. Spec draft submitted as MCP RFC / GitHub discussion.
3. Coordinate with other MCP server authors who have rolled their
   own auth — collect their requirements before locking the spec.

## Out of scope

- Authorization model (what identities can do).
- Multi-tenancy / org-scoped identity.
- Delegation / on-behalf-of flows.
- Specific provider implementations beyond the initial reference
  set.
- UI/UX for token issuance (provider-specific concern).

## Sequencing

1. **PAL-level interim first.** Define `IdentityProvider` interface,
   implement the four reference providers, refactor PAL to use them.
   Delivers immediate value (Tailscale support, simpler config) and
   creates the working reference for the upstream conversation.
2. **Extract a clean RFC** from PAL's experience and open an MCP
   discussion / issue. Lead with concrete examples (the Tailscale
   case, PAL's OAuth deletion) rather than abstract design.
3. **If upstream accepts**, migrate PAL's internal interface to
   match the standard. Rest of the code is unchanged.
4. **If upstream declines**, PAL still benefits and the pattern
   exists as a working example for other server authors who want to
   adopt it.

## Relationship to other briefs

This brief is **independent** of the pipeline-grammar and
protocol-header-hoist briefs — they affect command parsing and
per-call token overhead, while this one affects authentication. The
three can be implemented in any order without conflict.

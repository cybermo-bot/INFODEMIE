# Security boundary

This build includes an isolated demonstration and a separate local installation with personal accounts. Public production initialization deliberately throws unless an approved identity implementation is added. Bind web and API to loopback. Never expose fixture accounts to the public internet or place institutional data into the demo database. Local mode enforces loopback client/hostname and a fixed localhost frontend origin. An unpredictable one-time installation code protects first-account creation; a unique transaction marker prevents simultaneous bootstrap. Local accounts use dedicated typed creation/reset operations, explicit roles, forced initial password replacement and session revocation.

The backend authenticates opaque bearer sessions stored as SHA-256 token digests; passwords use PBKDF2-HMAC-SHA256 with unique salts and 310000 iterations. Sessions expire in eight hours and logout revokes the current token. The UI stores the development token in sessionStorage, so a production XSS mitigation/identity design is still required. There is no cookie authentication/CSRF boundary to configure in this build.

Object access requires institution match before returning the object. Role checks apply to direct API mutations, not only menus. Generic user edits only permit active-state changes; local administrators explicitly select roles when creating new accounts through the dedicated audited endpoint. Source/data inputs cannot change permission checks or execute commands. Evidence citations must resolve to stored approved source/document versions and passage IDs.

Report exports require an approved scoped report. CSV cells beginning with spreadsheet formula prefixes are escaped. Audit records omit password hashes and secrets. A first-pass regular expression redactor removes email, handles and phone patterns; analysts must inspect residual identifiers, names and contextual identifiability.

RSS URLs require public HTTPS, no URL credentials, standard port, public resolved addresses, no redirects, 15-second timeout and 2MB content ceiling. Entity declarations are rejected. An egress proxy/firewall and DNS pinning remain required before untrusted live source administration; the initial DNS check alone does not eliminate rebinding.

Audit is append-only through the normal application API. Privacy deletion may redact affected historical payloads and is itself audited; complete backup/index retention enforcement remains release work. Generic JSON storage does not yet provide all required database-level relationships, tamper resistance or high-concurrency guarantees.

Threat-model and penetration-test the deployment; finish OIDC/MFA, distributed rate limits, TLS, encryption at rest, CSP, observability, malware scanning and restore drills before approving a live pilot.

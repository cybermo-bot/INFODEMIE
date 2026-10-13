# Official social API tracking on this PC

Implemented: selected public YouTube video statistics, Bluesky public post counters, public Mastodon status counters and X public post metrics with approved API access. Automatic topic discovery is available through official YouTube and X search, permitted Bluesky public search and Mastodon public hashtag timelines. This is bounded keyword/hashtag monitoring, not full social listening, unique audience measurement, clinical rumour detection or geographically representative surveillance. The existing RSS connector also accepts explicitly permitted public HTTPS feeds, which generally do not expose social engagement.

In Overview, open **Suivi des publications sociales**, add original individual publication links, document the purpose and review the source terms, then press **Interroger les API**. Up to 20 targets; manual refresh is limited to one attempt per minute per institution. The API verifies YouTube public status, resolves Bluesky identities through the official public API, reports unavailable content and missing counters honestly, and does not bypass denied access. A configured key does not prove the connection works; only an actual successful observation does.

## YouTube key configuration

Create your own Google Cloud project, enable **YouTube Data API v3**, and create a restricted API key. Keep it out of chat, screenshots, source code and URLs shared with clients. Put this JSON in the ignored local file `data/social-credentials.json`:

```json

{"youtube_api_key": "YOUR_RESTRICTED_API_KEY"}

```

Alternatively set the server environment variable `YOUTUBE_API_KEY`. The local file is read on each request, so no restart is needed. Restrict the key to the YouTube Data API and appropriate server access; do not put it in frontend environment variables. Follow quota and application compliance requirements in Google's console. The application performs read-only `search.list` and `videos.list` calls, never uploads or comments. It does not use OAuth or private/unlisted video data. Do not treat API availability as blanket permission for any downstream use.

Bluesky uses its published public AppView API for selected posts and requires no key for these endpoints when the service allows them. HTTP denial is shown; no alternate host or scraping fallback is attempted.

## Privacy and measurement

The database stores the selected URL, monitoring purpose and administrator's terms acknowledgment. URLs can identify authors: choose a justified monitoring scope and avoid sensitive personal information in the purpose. Selected-post API responses remain in process memory for 15 minutes; automatic discovery responses expire after the polling interval plus 15 minutes (75 minutes normally, 135 minutes for Mastodon); they are not written to the database, audit snapshots, reports or backups. No full post bodies, authors, media or commenter identities are copied. Restart clears the transient observations. A failed refresh clears prior observations for that platform request. Removing a target removes its active record, version history and audit URL/purpose; existing offline backups require separate deletion/restore handling.

Display metrics only as returned by the source, with observation time and original link. Missing values are unknown. Do not sum YouTube views and Bluesky reposts, infer people reached, compute a viral score, claim historical change from these observations or use them as a medical verdict. Historical storage, full archive discovery and additional derived metrics require separate engineering and policy review.

## Other platforms

Facebook/Instagram, TikTok, Reddit and Telegram are explicitly **not implemented** here. They require their respective official access, account/page/server scope, platform permission and source-specific adapters. A key alone will not activate them. There is no lawful universal key providing all platforms or private conversations. Supply the desired sources and permitted access before extending these adapters.

Official references: [YouTube videos.list](https://developers.google.com/youtube/v3/docs/videos/list), [YouTube API developer policies](https://developers.google.com/youtube/terms/developer-policies), [policy compliance guide](https://developers.google.com/youtube/terms/developer-policies-guide), [Google privacy](https://policies.google.com/privacy), [YouTube terms](https://www.youtube.com/t/terms), [Bluesky API hosts](https://docs.bsky.app/docs/advanced-guides/api-directory), [Bluesky terms](https://bsky.social/about/support/tos).

This local implementation is not a platform-policy approval, legal certification or a completed production social-listening system.

## Mastodon

Add the original public status URL from the relevant Mastodon server. The connector validates public HTTPS destinations, rejects private/reserved addresses and redirects, and calls only `/api/v1/statuses/{id}`. Only statuses returned with `visibility=public` produce metrics. Servers may restrict access or require an account token: store tokens by exact hostname in `data/social-credentials.json`, e.g. `"mastodon_tokens": {"your-server.example": "YOUR_READ_ONLY_TOKEN"}`. The token is sent only to that hostname, never to a redirect. Review that server's rules and obtain permitted access first. Public counts reflect the server's federated view, which may be incomplete; no global coverage is claimed. [Official Mastodon status API](https://docs.joinmastodon.org/methods/statuses/).

## X

The official post-lookup adapter requires your approved X developer project and a bearer token with access/quota for `GET https://api.x.com/2/tweets`. Add `"x_bearer_token": "YOUR_TOKEN"` to the same ignored local credentials JSON, or set server environment variable `X_BEARER_TOKEN`. Add an original `https://x.com/user/status/ID` link in the dashboard. Only returned public metrics are displayed; unavailable posts and omitted metrics remain unavailable/unknown. No author profiles, post bodies, historical datasets or private conversations are stored. Access can require payment and is subject to X policies; a token does not guarantee entitlement. [Official X post lookup documentation](https://docs.x.com/x-api/posts/lookup/introduction).

Reddit is not activated for this client use: commercial Data API use requires a separate agreement under [Reddit's Data API terms](https://redditinc.com/policies/data-api-terms). Facebook/Instagram and TikTok similarly need suitable approved access and source-specific implementations; they do not provide unrestricted listening through a generic key.


## Automatic watch

The local API starts a background monitoring thread independent of browser tabs. Keep PNSI running and this PC awake and connected. Saved target metrics refresh every 10 minutes by default (administrator can pause/resume; the API accepts 5/10/15/30/60 minutes). Up to four configured topic watches search hourly; Mastodon hashtag watches run every two hours. Each search returns at most ten distinct results over the last seven days, without archive pagination. All observed data is transient, attributed to its API and timestamped. An error clears old observations for that watch. Queries, purpose, schedule, attempts and error state persist; post bodies, authors and engagement measurements do not enter generic records or backups.

The owner requested a broad health preset with vaccination, measles and health keywords in French, English, Arabic and Derja/Arabizi. One watch per provider is configured; Mastodon uses `mastodon.social` public hashtags. This is a multilingual query scope, not validated language detection or a claim to cover every health assertion. Geographic coverage remains unknown. The maintenance audit records the owner request and does not fabricate a platform-terms acceptance. Credentials still require suitable provider access and use-case compliance.

Default failures back off exponentially to 8 hours for discovery (6 hours for saved targets); valid provider Retry-After delays are respected. A waiting YouTube/X watch wakes within the next 30-second scheduler check after credentials become available. Each provider has a local ceiling of 80 search requests per UTC day; provider limits can be lower. Successful watches refresh after restart to replace the lost transient cache; denied-source cooldowns remain in effect. Daily counters are operational metadata, not engagement data. RSS collection continues separately every 30 minutes.

Live checkpoint on 2026-10-11: YouTube and Mastodon returned 20 social publications in the first automatic cycle. The YouTube key was configured by the owner; X remains unconfigured. Bluesky public search returned HTTP 403 and was not bypassed. Public getPosts availability does not guarantee public search access. See the live verification artifact for current counts, states and times.

References: [YouTube official search](https://developers.google.com/youtube/v3/docs/search/list), [X recent search](https://docs.x.com/x-api/posts/search-recent-posts), [Mastodon hashtag timelines](https://docs.joinmastodon.org/methods/timelines/).

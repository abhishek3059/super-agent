# Third-party notices

## Bot HQ

`apps/hq` is adapted from [Bot HQ](https://github.com/nickvasilescu/bot-hq)
at commit `decf9a215cddd8792a5f20f4a11a87d4dffa6d15`, used under the MIT
license. The full license text is in [LICENSE.bot-hq](LICENSE.bot-hq).
Copyright (c) 2026 Nick Vasilescu.

Changes made here: the Orgo cloud computer, VNC relay and Google sign-in
were removed. Each bot gets a local Chrome and a DevTools screen relay. Voice
uses OpenAI Realtime. Composio and xAI are optional. Handoffs between bots
return automatically. Skins were added.

Bot HQ's bot artwork, UI icons and app logos are **not** included. Its
notices say that artwork comes from another product and is not covered by
the MIT license. The bot shapes in `web/src/avatar/shapes.ts` and the
favicon were made for this project.

## Lucide icons

UI icons come from [Lucide](https://lucide.dev) through the `lucide-react`
package, under the ISC license. Some Lucide icons derive from
[Feather](https://feathericons.com) (MIT, Copyright (c) 2013-present Cole
Bemis). The license texts ship inside the package.

## npm dependencies

Other dependencies are covered by the licenses in their packages. See
`package-lock.json` for exact versions.

# R-01.5: credential design review

| Field | Value |
| --- | --- |
| Date | 2026-11-10 |
| Evidence | [Review record](../reviews/r01-5-credential-design.md), [design section 7](../design/voice-foundation.md#7-credential-design-r-015) |

## What happened

An independent security reviewer (a different tool and model from the design
author) reviewed the local credential design. The first pass was ACCEPT WITH
CONDITIONS with one HIGH and three MEDIUM findings. After two revision rounds
the design-stage verdict was ACCEPT.

## What we learned

- On a single-user loopback service, a hard failed-auth lockout is itself the attack: any local process can keep the real user out. With a 256-bit token, throttling only needs to limit abuse, and a correct token should always get in.
- Fixing one availability problem can create another. The pre-auth connection cap added for CR-06 could be filled by attempts held open during their delay (N1); closing failed attempts immediately fixed both.
- "Stored in the environment" is not a storage design. Say how the secret is generated, where it lives on each OS (0600 on macOS, owner-only ACL on Windows), and keep it out of shell history.
- SameSite=Strict does not separate localhost ports. Exact Origin and Host checks are the real CSRF control for a loopback app.
- The reviewer's claims about current code were checked against `app.py` and `config.py` before being recorded.

## What to do differently

Run a security review on each design section before implementation, not after, and keep the required negative tests in the review record so R-01.6 can start from them.

## Still unknown

Whether the implementation meets the design. That is R-01.6, which must run the nine listed negative tests plus the N1 and N2 tests.

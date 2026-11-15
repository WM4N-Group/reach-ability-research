# Source-live-video postprocess only; NOT T-COMPLEX experiment completion

Reuse existing direct-live raw_frames and exactRGB FFV1 decode verifier. Adds same-physical-tick side-by-side1x (optional common speed), original panels copied unchanged, captions outside source pixels, black ENDED panel after original terminal tick with literal end clock/status. No last-frame hold, independent time stretch, nearest/interpolation, resize, state replay, renderer or physics. A JSONL maps every presentation frame back to actual source ticks or explicit non-experiment ended panels. Common camera/resolution/rate and complete capture grid are mandatory; missing epochs fail closed.

Three pure clock checks passed. Remote engineering QA used existing closed TRAIN01/02 DIRECT-LIVE192x128 masters: each1x encoder exactRGB verified, pair1211frames/384x160 including32px footer exactRGB verified, raw sources/current H/active scope unchanged. These QA movies are explicitly NOT complex-scene results/HD capture; T-COMPLEX native/video count stays0.

Found real codec restriction: existing slices1 worked for192x128 singles but failed paired384x160. Failed output/error and pre-fix source retained. New postprocess copy uses supported4slices, keeping exactRGB decode checks; a one-frame960x540 SOFTWARE codec smoke roundtrip passed, not a real HD frame or GL/native qualification. Actual new scene camera/offscreen/live960x540 workload still needs same fresh-program zero/admission, with complete A/B raw masters. Missing footage cannot be repaired by replay/closed-arm reruns.

All raw/video outputs stay on46308. Only code/tests and this scalar explanation in Git.

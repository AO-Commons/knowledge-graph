# Social preview

`social-preview.png` — 1280×640, the card GitHub shows when the repository is
linked in Slack, on X, or anywhere that reads Open Graph tags. Without it they
show GitHub's generic grey card.

**It has to be uploaded by hand.** There is no API for it:
*Settings → General → Social preview → Edit → Upload an image*.

`social-preview.html` is what it was rendered from, so the figures can be
brought up to date without redrawing anything:

```bash
python3 scripts/build_site.py          # for the current counts
open .github/brand/social-preview.html # edit the four figures
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless --window-size=1280,640 --hide-scrollbars \
  --screenshot=.github/brand/social-preview.png \
  --virtual-time-budget=8000 file://$PWD/.github/brand/social-preview.html
```

AO Commons tokens, same as the site: the sky-to-background gradient, Bricolage
Grotesque for the display face, DM Mono for the labels, and the green rule.

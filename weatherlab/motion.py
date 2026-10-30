"""Gauge animation: the sweep and fill that plays when a gauge appears. GAUGE_ANIM is copied exactly from the
dashboard's wxdash/live.py, and add() mirrors its animated() wrapper. The script animates any needle (a polygon with a
rotate transform), ring (a circle with a stroke-dasharray) and temperature segment (a path with stroke-width 22) it
finds, so it only runs inside st.iframe panels (0.37.41), where scripts execute. See SOURCES.md."""

GAUGE_ANIM = r"""
<script>
(function () {
  try {
    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    var DUR = 900;
    var ease = function (t) { return 1 - Math.pow(1 - t, 3); };
    var needles = [], rings = [], segs = [];
    document.querySelectorAll('polygon[transform^="rotate("]').forEach(function (el) {
      var m = /rotate\(\s*(-?[\d.]+)[\s,]+(-?[\d.]+)[\s,]+(-?[\d.]+)\s*\)/.exec(el.getAttribute('transform'));
      if (!m) return;
      var a = parseFloat(m[1]);
      var delta = (((a % 360) + 540) % 360) - 180;
      needles.push({el: el, from: a - delta, to: a, x: m[2], y: m[3]});
    });
    document.querySelectorAll('circle[stroke-dasharray]').forEach(function (el) {
      var parts = el.getAttribute('stroke-dasharray').split(',');
      var v = parseFloat(parts[0]);
      if (isNaN(v)) return;
      rings.push({el: el, v: v, rest: parts.slice(1).join(',') || '1000'});
    });
    document.querySelectorAll('svg path[stroke-width="22"]').forEach(function (el) { segs.push(el); });
    if (!needles.length && !rings.length && !segs.length) return;
    needles.forEach(function (n) { n.el.setAttribute('transform', 'rotate(' + n.from + ' ' + n.x + ' ' + n.y + ')'); });
    rings.forEach(function (r) { r.el.setAttribute('stroke-dasharray', '0.001,' + r.rest); });
    segs.forEach(function (s) { s.style.opacity = 0; });
    var t0 = null;
    function frame(ts) {
      if (t0 === null) t0 = ts;
      var p = Math.min((ts - t0) / DUR, 1), e = ease(p);
      needles.forEach(function (n) {
        n.el.setAttribute('transform', 'rotate(' + (n.from + (n.to - n.from) * e) + ' ' + n.x + ' ' + n.y + ')');
      });
      rings.forEach(function (r) { r.el.setAttribute('stroke-dasharray', Math.max(r.v * e, 0.001) + ',' + r.rest); });
      var shown = Math.ceil(p * segs.length);
      segs.forEach(function (s, i) { s.style.opacity = i < shown ? 1 : 0; });
      if (p < 1) requestAnimationFrame(frame);
      else {
        needles.forEach(function (n) { n.el.setAttribute('transform', 'rotate(' + n.to + ' ' + n.x + ' ' + n.y + ')'); });
        rings.forEach(function (r) { r.el.setAttribute('stroke-dasharray', r.v + ',' + r.rest); });
        segs.forEach(function (s) { s.style.opacity = 1; });
      }
    }
    requestAnimationFrame(frame);
  } catch (err) { /* leave the static gauge as drawn */ }
})();
</script>
"""


def add(html: str, on: bool) -> str:
    """The panel's HTML, with the animation script added when animations are on."""
    return html + GAUGE_ANIM if on else html

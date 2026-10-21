"""Embedded panels that fit their content. Each components.html panel grows or shrinks to what is inside, and a panel
a little too wide for a phone is scaled down instead of cut off. Copied from the dashboard's wxdash/live_glue.py
(_FIT_JS and install_autofit); see SOURCES.md."""

import streamlit.components.v1 as components

_FIT_JS = """<script>(function(){
 function fit(){
  var f=window.frameElement, b=document.body; if(!f||!b) return;
  var de=document.documentElement;
  b.style.zoom=''; var cw=de.clientWidth, sw=Math.max(de.scrollWidth,b.scrollWidth);
  if(sw>cw+2){ b.style.zoom=(cw/sw).toFixed(3); }
  var cs=getComputedStyle(b), z=parseFloat(b.style.zoom||'1');
  var h=Math.ceil((b.scrollHeight+parseFloat(cs.marginTop)+parseFloat(cs.marginBottom))*z)+2;
  if(h>20 && Math.abs(f.offsetHeight-h)>4){ f.style.height=h+'px'; f.setAttribute('height',h); }
  try{ var w=f.parentElement, n=0;
    while(w && n<3){ if(w.getAttribute && w.getAttribute('data-testid')==='stElementContainer'){ w.style.setProperty('height',h+'px','important'); w.style.minHeight=h+'px'; break; } w=w.parentElement; n++; }
  }catch(e){}
 }
 window.addEventListener('load',fit); setTimeout(fit,60); setTimeout(fit,500); setTimeout(fit,1500);
 try{ new ResizeObserver(function(){ fit(); }).observe(document.body); }catch(e){}
})();</script>"""


def install() -> None:
    """Wrap components.html so every panel gets the fitting script. Safe to call on every rerun."""
    cur = components.html
    if getattr(cur, "_wx_autofit", False):
        if getattr(cur, "_wx_js", None) == _FIT_JS:
            return
        orig = cur._wx_orig  # the script changed: wrap the original again
    else:
        orig = cur

    def html(body, *a, **k):
        try:
            body = str(body) + _FIT_JS
        except Exception:
            pass
        return orig(body, *a, **k)
    html._wx_autofit = True
    html._wx_js = _FIT_JS
    html._wx_orig = orig
    components.html = html

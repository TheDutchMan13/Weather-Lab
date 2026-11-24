"""Small line icons for the cards (0.37.62): one stroke colour, drawn on a 24 by 24 grid.

Drawn for Weather Lab, so they carry no licence. Each returns inline SVG; colour defaults to the text colour."""

PATHS = {
    "wind": '<path d="M3 8h11a3 3 0 1 0-3-3"/><path d="M3 12h16a3 3 0 1 1-3 3"/><path d="M3 16h7"/>',
    "drop": '<path d="M12 3c3.5 4.6 6 8 6 11a6 6 0 0 1-12 0c0-3 2.5-6.4 6-11z"/>',
    "gauge": '<path d="M4.5 17a8.5 8.5 0 1 1 15 0"/><path d="M12 13l4-4"/><circle cx="12" cy="13.5" r="1.2"/>'
             '<path d="M7 9.5l.8.8M12 6.5v1.2M17 9.5l-.8.8"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2.5v2.5M12 19v2.5M2.5 12H5M19 12h2.5M5.3 5.3l1.8 1.8'
           'M16.9 16.9l1.8 1.8M5.3 18.7l1.8-1.8M16.9 7.1l1.8-1.8"/>',
    "rain": '<path d="M7 16a4.5 4.5 0 0 1-.6-9A6 6 0 0 1 18 8.5a3.8 3.8 0 0 1-.5 7.5H7z"/>'
            '<path d="M8.5 19l-.8 2M12.5 19l-.8 2M16.5 19l-.8 2"/>',
    "thermo": '<path d="M10 4a2 2 0 1 1 4 0v9.3a4 4 0 1 1-4 0z"/><path d="M12 9v6"/>',
    "sunset": '<path d="M4 18h16M7 21h10"/><path d="M7.5 18a4.5 4.5 0 0 1 9 0"/><path d="M12 6v4M9.5 9.5 12 12l2.5-2.5"/>'
              '<path d="M3.5 13.5l1.5.8M20.5 13.5l-1.5.8"/>',
    "sunrise": '<path d="M4 18h16M7 21h10"/><path d="M7.5 18a4.5 4.5 0 0 1 9 0"/><path d="M12 12V8M9.5 10.5 12 8l2.5 2.5"/>'
               '<path d="M3.5 13.5l1.5.8M20.5 13.5l-1.5.8"/>',
    "check": '<circle cx="12" cy="12" r="9"/><path d="M8 12.5l2.7 2.7L16.5 9"/>',
    "alert": '<path d="M12 3.5 21.5 20h-19z"/><path d="M12 10v4.5M12 17.2v.3"/>',
    "station": '<path d="M12 21V9M8 21h8"/><path d="M6 6.5a8 8 0 0 1 12 0M8.5 9a4.5 4.5 0 0 1 7 0"/>'
               '<circle cx="12" cy="11" r="1"/>',
    "pin": '<path d="M12 21s6.5-6.2 6.5-11.5a6.5 6.5 0 0 0-13 0C5.5 14.8 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.3"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5.5l3.5 2"/>',
}


def icon(name: str, size: int = 22, color: str = "currentColor", width: float = 1.8) -> str:
    """Inline SVG for one icon. Unknown names give an empty string."""
    body = PATHS.get(name)
    if body is None:
        return ""
    return (f'<svg viewBox="0 0 24 24" width="{size}" height="{size}" fill="none" stroke="{color}" '
            f'stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" '
            f'style="flex:0 0 auto;vertical-align:middle">{body}</svg>')

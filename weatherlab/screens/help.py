"""Help and glossary: plain-words explanations of the terms shown next to the numbers."""
import streamlit as st

from weatherlab import glossary, theme


def help_page() -> None:
    st.markdown(theme.page_head("Help and glossary", "What the terms next to the numbers mean."), unsafe_allow_html=True)
    typed = st.text_input("Search", placeholder="Try dew, pressure or UV", key="glossary_search")
    found = glossary.search(typed)
    if not found:
        st.caption("No term matches. Try a shorter word.")
        return
    for t in found:
        with st.container(border=True):
            st.markdown(f"**{t['name']}**")
            st.markdown(t["long"])
    st.caption("Explanations are general. Your station's numbers come from its own sensors.")

"""Streamlit UI: enter a natural language prompt, see it translated into
LogQL, PromQL, and MQL, and browse past benchmark runs."""

import json

import streamlit as st
from dotenv import load_dotenv

from .benchmark import RESULTS_DIR
from .query_languages import SUPPORTED_LANGUAGES
from .translator import QueryTranslator

load_dotenv()

st.set_page_config(page_title="NL Telemetry Query Generator", layout="wide")
st.title("Natural Language Telemetry Query Generator")

tab_translate, tab_benchmark = st.tabs(["Translate", "Benchmark Results"])

with tab_translate:
    nl_prompt = st.text_input(
        "Describe the query you want",
        placeholder="e.g. show me 5xx errors from the checkout service in the last hour",
    )

    if st.button("Translate", disabled=not nl_prompt):
        translator = QueryTranslator()
        with st.spinner("Translating..."):
            queries = translator.translate_all(nl_prompt)

        cols = st.columns(len(SUPPORTED_LANGUAGES))
        for col, (lang_key, spec) in zip(cols, SUPPORTED_LANGUAGES.items()):
            with col:
                st.subheader(spec.name)
                st.code(queries[lang_key], language="text")

with tab_benchmark:
    result_files = sorted(RESULTS_DIR.glob("*.json")) if RESULTS_DIR.exists() else []

    if not result_files:
        st.info("No benchmark runs yet. Run `python -m src.benchmark` to generate one.")
    else:
        selected = st.selectbox(
            "Benchmark run", options=result_files, format_func=lambda p: p.name
        )
        data = json.loads(selected.read_text())
        st.dataframe(data, use_container_width=True)

        avg_latency = {}
        for row in data:
            avg_latency.setdefault(row["model"], []).append(row["latency_seconds"])
        st.subheader("Average latency by model (seconds)")
        st.bar_chart(
            {model: sum(vals) / len(vals) for model, vals in avg_latency.items()}
        )

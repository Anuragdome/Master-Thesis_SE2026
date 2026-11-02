import os
import json
import shutil
import tempfile
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.express as px
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components


# ----------------------------
# Streamlit Page Config
# ----------------------------
st.set_page_config(
    page_title="Knowledge Graph Pipeline",
    page_icon="🧠",
    layout="wide"
)

st.title("🧠 Knowledge Graph Pipeline")
st.write("Upload a document, extract triples, and visualize the knowledge graph.")


# ----------------------------
# Sidebar Settings
# ----------------------------
st.sidebar.header("⚙️ Settings")

st.sidebar.subheader("Multi-LLM Consensus")
st.sidebar.caption(
    "Three independent models each build their own graph; triples are only "
    "kept if the OTHER models agree they're supported by the source text."
)

use_gemini = st.sidebar.checkbox("Use Gemini (hosted API)", value=True)
gemini_model_name = st.sidebar.text_input("Gemini model", value="gemini-2.5-flash", disabled=not use_gemini)
api_key = st.sidebar.text_input(
    "Gemini API Key",
    type="password",
    placeholder="Paste your Gemini key",
    disabled=not use_gemini,
)

use_llama = st.sidebar.checkbox("Use Llama 3.1 8B (Ollama, local)", value=True)
llama_model_name = st.sidebar.text_input("Llama model tag", value="llama3.1:8b", disabled=not use_llama)

use_qwen = st.sidebar.checkbox("Use Qwen 3 8B (Ollama, local)", value=True)
qwen_model_name = st.sidebar.text_input("Qwen model tag", value="qwen3:8b", disabled=not use_qwen)

ollama_url = st.sidebar.text_input("Ollama URL", value="http://localhost:11434")

min_agreement_score = st.sidebar.select_slider(
    "Minimum Agreement Score",
    options=[0.0, 0.5, 1.0],
    value=0.5,
    help="Fraction of verifying models that must confirm a triple for it to enter the Consensus Knowledge Graph.",
)

st.sidebar.divider()
use_neo4j = st.sidebar.checkbox("Use Neo4j", value=False)

run_button = st.sidebar.button("🚀 Run Pipeline")


# ----------------------------
# File Upload
# ----------------------------
uploaded_files = st.file_uploader(
    "Upload documents",
    type=["txt", "pdf", "html", "htm"],
    accept_multiple_files=True
)


# ----------------------------
# Helper: Build Graph Visualization
# ----------------------------
def create_pyvis_graph(triples_df):
    graph = nx.MultiDiGraph()

    for _, row in triples_df.iterrows():
        subject = row["subject"]
        obj = row["object"]
        relation = row["relation"]

        graph.add_node(subject, title=row.get("subject_type", "ENTITY"))
        graph.add_node(obj, title=row.get("object_type", "ENTITY"))
        graph.add_edge(subject, obj, label=relation)

    net = Network(
        height="650px",
        width="100%",
        bgcolor="#ffffff",
        font_color="black",
        directed=True
    )

    net.from_nx(graph)

    for node in net.nodes:
        node["size"] = 18
        node["font"] = {"size": 16}

    for edge in net.edges:
        edge["font"] = {"size": 12, "align": "middle"}
        edge["arrows"] = "to"

    net.repulsion(
        node_distance=180,
        central_gravity=0.2,
        spring_length=200,
        spring_strength=0.05
    )

    html_path = "kg_graph.html"
    net.save_graph(html_path)

    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    return html


# ----------------------------
# Run Pipeline
# ----------------------------
if run_button:
    if not uploaded_files:
        st.error("Please upload at least one document.")
        st.stop()

    n_enabled = sum([use_gemini, use_llama, use_qwen])
    if n_enabled < 2:
        st.warning(
            "Fewer than 2 models enabled — the pipeline will fall back to the "
            "legacy single-model (or mock) mode instead of Multi-LLM Consensus."
        )
    if use_gemini and not api_key:
        st.warning("Gemini is enabled but no API key was provided — it will be skipped.")

    with st.spinner("Running knowledge graph pipeline (this calls 3 models concurrently)..."):

        # Create temporary input folder
        temp_dir = Path(tempfile.mkdtemp())
        input_dir = temp_dir / "input_docs"
        input_dir.mkdir(parents=True, exist_ok=True)

        for uploaded_file in uploaded_files:
            file_path = input_dir / uploaded_file.name
            with open(file_path, "wb") as f:
                f.write(uploaded_file.read())

        if use_gemini and api_key:
            os.environ["GEMINI_API_KEY"] = api_key

        # Import config and override values
        import config.settings as cfg

        cfg.NEO4J_ENABLED = use_neo4j

        # ── Multi-LLM Consensus settings ──
        cfg.USE_GEMINI = use_gemini
        cfg.USE_LLAMA = use_llama
        cfg.USE_QWEN = use_qwen
        cfg.MODEL_NAME = gemini_model_name
        cfg.LLAMA_MODEL_NAME = llama_model_name
        cfg.QWEN_MODEL_NAME = qwen_model_name
        cfg.OLLAMA_URL = ollama_url
        cfg.MIN_AGREEMENT_SCORE = min_agreement_score
        if use_gemini and api_key:
            cfg.GEMINI_API_KEY = api_key

        from src.pipeline import Pipeline

        pipeline = Pipeline(config_module=cfg)
        results = pipeline.run(input_dir=input_dir)

        st.session_state["results"] = results
        st.session_state["output_dir"] = Path("data/output")
        st.session_state["processed_dir"] = Path("data/processed")

    mode = results.get("pipeline_mode", "unknown")
    if mode == "consensus":
        st.success(
            f"Consensus pipeline completed! Models used: {', '.join(results.get('providers_used', []))}"
        )
    else:
        st.success("Pipeline completed (legacy single-model / demo mode).")


# ----------------------------
# Show Results
# ----------------------------
if "results" in st.session_state:
    results = st.session_state["results"]
    output_dir = st.session_state["output_dir"]
    processed_dir = st.session_state["processed_dir"]

    st.header("📊 Pipeline Summary")

    mode = results.get("pipeline_mode", "legacy")
    graph_stats = results.get("graph", {})
    extraction_stats = results.get("extraction", {})
    relation_analysis = results.get("relation_analysis", {})
    entity_coverage = results.get("entity_coverage", {})
    consensus_stats = results.get("consensus", {})
    per_model_stats = results.get("per_model_stats", {})
    provider_model_names = results.get("provider_model_names", {})
    providers_used = results.get("providers_used", [])

    def _model_label(provider_key: str) -> str:
        """'gemini' -> 'Gemini (gemini-2.5-flash)' using the actual
        configured model name for that provider, falling back to just the
        provider key if no model name was recorded."""
        actual_name = provider_model_names.get(provider_key)
        display = provider_key.replace("_", " ").title()
        return f"{display} ({actual_name})" if actual_name else display

    graph_col1, graph_col2 = st.columns(2)
    graph_col1.metric("Nodes", graph_stats.get("nodes", 0))
    graph_col2.metric("Edges", graph_stats.get("edges", 0))

    if mode == "consensus":
        st.subheader("Triples Generated per Model")
        if per_model_stats:
            model_cols = st.columns(len(per_model_stats))
            for col, (model_key, stats) in zip(model_cols, per_model_stats.items()):
                col.metric(_model_label(model_key), stats.get("triples_generated", 0))
        else:
            st.info("No per-model extraction statistics available.")

        st.subheader("Consensus Results")
        cc1, cc2, cc3, cc4 = st.columns(4)
        cc1.metric("Total Candidate Triples", consensus_stats.get("total_candidate_triples", 0))
        cc2.metric("Total Accepted Triples", consensus_stats.get("accepted", 0))
        cc3.metric("Total Rejected Triples", consensus_stats.get("rejected", 0))
        cc4.metric("Acceptance Rate", f"{consensus_stats.get('acceptance_rate', 0):.1%}")
    else:
        st.subheader("Triples Generated")
        if providers_used:
            label = _model_label(providers_used[0])
        else:
            label = "Mock / demo extraction (no model configured or reachable)"
        st.metric(label, extraction_stats.get("total_raw_triples", 0))
        st.caption(
            "Fewer than 2 models were enabled or reachable, so this run used the "
            "legacy single-model pipeline. Consensus metrics (candidate/accepted/"
            "rejected/acceptance rate) require at least 2 models cross-verifying "
            "each other and are not available for this run."
        )

    st.divider()

    triples_path = output_dir / "triples.csv"

    if triples_path.exists():
        triples_df = pd.read_csv(triples_path)

        tab_names = [
            "📄 Extracted Triples",
            "🕸️ Knowledge Graph",
            "📊 Analytics",
            "🧩 Entities",
            "📥 Downloads",
        ]
        if mode == "consensus":
            tab_names.insert(3, "🤝 Consensus")

        tabs = st.tabs(tab_names)
        tab1, tab2, tab3 = tabs[0], tabs[1], tabs[2]
        if mode == "consensus":
            tab_consensus = tabs[3]
            tab4, tab5 = tabs[4], tabs[5]
        else:
            tab4, tab5 = tabs[3], tabs[4]

        with tab1:
            st.subheader("Extracted Knowledge Triples")
            st.dataframe(triples_df, use_container_width=True)

        with tab2:
            st.subheader("Interactive Knowledge Graph")

            if len(triples_df) > 0:
                graph_html = create_pyvis_graph(triples_df)
                components.html(graph_html, height=700, scrolling=True)
            else:
                st.warning("No triples found to visualize.")

        with tab3:
            st.subheader("Relation Analysis")

            if "relation" in triples_df.columns:
                rel_counts = triples_df["relation"].value_counts().reset_index()
                rel_counts.columns = ["relation", "count"]

                fig = px.bar(
                    rel_counts,
                    x="relation",
                    y="count",
                    title="Most Common Relations"
                )
                st.plotly_chart(fig, use_container_width=True)

            if "confidence" in triples_df.columns:
                fig2 = px.histogram(
                    triples_df,
                    x="confidence",
                    nbins=10,
                    title="Confidence Score Distribution"
                )
                st.plotly_chart(fig2, use_container_width=True)

            st.json(results)

        if mode == "consensus":
            with tab_consensus:
                st.subheader("Multi-LLM Consensus Verification")

                per_model = results.get("per_model_stats", {})
                if per_model:
                    st.markdown("**Per-model statistics** (Step 9)")
                    per_model_df = pd.DataFrame(per_model).T
                    st.dataframe(per_model_df, use_container_width=True)

                    fig_agree = px.bar(
                        per_model_df.reset_index().rename(columns={"index": "model"}),
                        x="model",
                        y="average_agreement_score",
                        title="Average Agreement Score by Generating Model",
                        range_y=[0, 1],
                    )
                    st.plotly_chart(fig_agree, use_container_width=True)

                st.markdown("**Consensus / hallucination reduction**")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Accepted (passed consensus rule)", consensus_stats.get("accepted", 0))
                c2.metric("Rejected", consensus_stats.get("rejected", 0))
                c3.metric("Acceptance rate", f"{consensus_stats.get('acceptance_rate', 0):.1%}")
                c4.metric(
                    "Final graph triples (post-dedup)",
                    consensus_stats.get("consensus_graph_triples", 0),
                    help=(
                        "Accepted triples that describe the same fact (same "
                        "subject/relation/object after alignment) are merged "
                        "into one edge — this is the actual size of the "
                        "Consensus Knowledge Graph."
                    ),
                )

                dist = consensus_stats.get("agreement_score_distribution", {})
                if dist:
                    dist_df = pd.DataFrame(
                        {"agreement_score": list(dist.keys()), "count": list(dist.values())}
                    )
                    fig_dist = px.bar(
                        dist_df, x="agreement_score", y="count",
                        title="Agreement Score Distribution",
                    )
                    st.plotly_chart(fig_dist, use_container_width=True)

                if "agreement_score" in triples_df.columns:
                    st.markdown("**Accepted triples with full metadata**")
                    show_cols = [
                        c for c in [
                            "subject", "relation", "object", "generator_model",
                            "agreement_score", "consensus_status", "verification_results",
                        ] if c in triples_df.columns
                    ]
                    st.dataframe(triples_df[show_cols], use_container_width=True)

                svc = results.get("single_vs_consensus")
                if svc and "improvement_over_single_model" in svc:
                    st.markdown("**Single model vs. Consensus graph (gold-standard F1)**")
                    imp = svc["improvement_over_single_model"]
                    imp_df = pd.DataFrame(imp).T
                    st.dataframe(imp_df, use_container_width=True)

        with tab4:
            entities_path = processed_dir / "entities.json"

            if entities_path.exists():
                entities = json.loads(entities_path.read_text(encoding="utf-8"))
                entities_df = pd.DataFrame(entities)
                st.dataframe(entities_df, use_container_width=True)
            else:
                st.info("No entities.json file found.")

        with tab5:
            st.subheader("Download Output Files")

            files = [
                output_dir / "triples.json",
                output_dir / "triples.csv",
                output_dir / "evaluation_results.json",
                output_dir / "evaluation_report.txt",
                output_dir / "import_graph.cypher",
                processed_dir / "chunks.json",
                processed_dir / "raw_triples.json",
                processed_dir / "raw_triples_by_model.json",
                processed_dir / "verified_triples.json",
                processed_dir / "consensus_triples.json",
                processed_dir / "entities.json",
            ]

            for file in files:
                if file.exists():
                    st.download_button(
                        label=f"Download {file.name}",
                        data=file.read_bytes(),
                        file_name=file.name
                    )

    else:
        st.warning("No triples.csv found. Please check pipeline errors.")
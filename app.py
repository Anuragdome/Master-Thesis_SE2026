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

provider = st.sidebar.selectbox(
    "LLM Provider",
    ["gemini", "openai", "anthropic"],
    index=0
)

model_name = st.sidebar.text_input(
    "Model Name",
    value="gemini-2.5-flash"
)

use_neo4j = st.sidebar.checkbox("Use Neo4j", value=False)

api_key = st.sidebar.text_input(
    "API Key",
    type="password",
    placeholder="Paste your Gemini/OpenAI/Claude key"
)

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

    if not api_key:
        st.warning("No API key provided. The pipeline may use mock/demo extraction.")

    with st.spinner("Running knowledge graph pipeline..."):

        # Create temporary input folder
        temp_dir = Path(tempfile.mkdtemp())
        input_dir = temp_dir / "input_docs"
        input_dir.mkdir(parents=True, exist_ok=True)

        for uploaded_file in uploaded_files:
            file_path = input_dir / uploaded_file.name
            with open(file_path, "wb") as f:
                f.write(uploaded_file.read())

        # Set API keys
        if provider == "gemini":
            os.environ["GEMINI_API_KEY"] = api_key
        elif provider == "openai":
            os.environ["OPENAI_API_KEY"] = api_key
        elif provider == "anthropic":
            os.environ["ANTHROPIC_API_KEY"] = api_key

        # Import config and override values
        import config.settings as cfg

        cfg.LLM_PROVIDER = provider
        cfg.MODEL_NAME = model_name
        cfg.NEO4J_ENABLED = use_neo4j

        if provider == "gemini":
            cfg.GEMINI_API_KEY = api_key
        elif provider == "openai":
            cfg.OPENAI_API_KEY = api_key
        elif provider == "anthropic":
            cfg.ANTHROPIC_API_KEY = api_key

        from src.pipeline import Pipeline

        pipeline = Pipeline(config_module=cfg)
        results = pipeline.run(input_dir=input_dir)

        st.session_state["results"] = results
        st.session_state["output_dir"] = Path("data/output")
        st.session_state["processed_dir"] = Path("data/processed")

    st.success("Pipeline completed!")


# ----------------------------
# Show Results
# ----------------------------
if "results" in st.session_state:
    results = st.session_state["results"]
    output_dir = st.session_state["output_dir"]
    processed_dir = st.session_state["processed_dir"]

    st.header("📊 Pipeline Summary")

    graph_stats = results.get("graph", {})
    extraction_stats = results.get("extraction", {})
    relation_analysis = results.get("relation_analysis", {})
    entity_coverage = results.get("entity_coverage", {})

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Nodes", graph_stats.get("nodes", 0))
    col2.metric("Edges", graph_stats.get("edges", 0))
    col3.metric("Raw Triples", extraction_stats.get("total_raw_triples", 0))
    col4.metric("Resolved Triples", extraction_stats.get("total_resolved_triples", 0))

    st.divider()

    triples_path = output_dir / "triples.csv"

    if triples_path.exists():
        triples_df = pd.read_csv(triples_path)

        tab1, tab2, tab3, tab4, tab5 = st.tabs(
            [
                "📄 Extracted Triples",
                "🕸️ Knowledge Graph",
                "📊 Analytics",
                "🧩 Entities",
                "📥 Downloads"
            ]
        )

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
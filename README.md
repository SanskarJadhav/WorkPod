# WorkPod: Groq Powered Project Collaboration Platform

![workpodtitle](https://github.com/SanskarJadhav/WorkPod/assets/113002227/18383d6f-3715-4d19-afa3-90e977e2f48f)

**Link:** [WorkPod](https://workpod.streamlit.app)

## Introduction

WorkPod is a Streamlit project collaboration tool built with SQLite, interactive dashboards, and LLM-assisted planning. It was originally created for the Snowflake Arctic hackathon using Snowflake Arctic Instruct through Replicate. The original Snowflake Arctic implementation is still available in the code as a legacy provider, but the deployed app now defaults to Groq's OpenAI-compatible API.

## Why the LLM Changed

The original Snowflake Arctic Instruct integration was functionally correct, but it depended on hosted inference credits. Once those credits ran out, WorkPod needed an online model provider that could continue working on Streamlit Cloud without requiring a local model server.

The new default is **Groq with Llama 3.1 8B Instant** because:

- It works in a deployed Streamlit Cloud app.
- It supports fast streaming chat completions through an OpenAI-compatible API.
- It can use `GROQ_API_KEY` from Streamlit secrets for the hosted app.
- Users can also enter their own Groq API key in the sidebar.
- The legacy Snowflake Arctic via Replicate path remains available if a Replicate token is provided.

## Features

- Registration and login for project workspaces.
- LLM-assisted project breakdowns that turn ideas into actionable tasks with estimated timelines.
- OneDash project dashboard with task progress, completion tracking, and contribution charts.
- Team collaboration through shared project IDs and member profiles.
- Oasis music recommendations, where the LLM maps a mood to normalized audio features and the app recommends matching songs from `musicdata.csv`.

## Tech Stack

- Streamlit for the web app.
- SQLite for local user and task storage.
- Groq's OpenAI-compatible chat completions API for the default LLM runtime.
- Meta Llama 3.1 8B Instant on Groq as the default model.
- Replicate + Snowflake Arctic Instruct retained as the legacy model provider.
- Plotly, Pandas, and NumPy for analytics and recommendations.

## Streamlit Cloud Setup

Add this secret in Streamlit Cloud:

```toml
GROQ_API_KEY = "your_groq_api_key_here"
```

The app also lets a visitor enter a Groq API key from the sidebar if no Streamlit secret is configured.

## Run Locally

1. Install Python dependencies:

```bash
pip install -r requirements.txt
```

2. Start the Streamlit app:

```bash
streamlit run run.py
```

3. Keep **Groq - Llama 3.1 8B Instant** selected in the sidebar and enter a Groq API key if one is not configured in secrets. To test the original Snowflake Arctic implementation, choose **Snowflake Arctic via Replicate (legacy)** and provide a Replicate API token.

## Configuration

The default Groq model can be changed with:

```bash
set WORKPOD_GROQ_MODEL=llama-3.1-8b-instant
```

## Developer

Created by Sanskar Jadhav for The Future of AI is Open Hackathon.

![SanskarJadhavheadshot](https://github.com/SanskarJadhav/WorkPod/assets/113002227/99c6976a-38f0-408d-8320-b4d39206b4cc)

import streamlit as st
from streamlit_extras.stylable_container import stylable_container
import sqlite3
import requests
from PIL import Image
import io
import replicate
import os
import re
import json
import plotly.express as px
import pandas as pd
import numpy as np

DEFAULT_GROQ_MODEL = os.getenv("WORKPOD_GROQ_MODEL", "llama-3.1-8b-instant")
GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"

# Set assistant icon to WorkPod logo for the default Groq LLM path
icons = {"assistant": "./WP.png", "user": "🐬"}


def stream_groq_chat(messages, api_key, model=DEFAULT_GROQ_MODEL, temperature=0.6):
    """Stream a chat response from Groq's OpenAI-compatible API."""
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        "temperature": temperature,
        "top_p": 0.9,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    try:
        response = requests.post(GROQ_CHAT_URL, headers=headers, json=payload, stream=True, timeout=(10, 180))
        response.raise_for_status()
    except requests.exceptions.HTTPError as exc:
        detail = exc.response.text if exc.response is not None else str(exc)
        st.error(
            f"Groq returned an error for `{model}`: {detail}. "
            "Check your GROQ_API_KEY and model name."
        )
        st.stop()
    except requests.exceptions.RequestException as exc:
        st.error(f"Groq request failed: {exc}")
        st.stop()

    for line in response.iter_lines():
        if not line:
            continue
        decoded_line = line.decode("utf-8")
        if not decoded_line.startswith("data: "):
            continue
        data = decoded_line.removeprefix("data: ").strip()
        if data == "[DONE]":
            break
        try:
            event = json.loads(data)
        except json.JSONDecodeError:
            continue

        chunk = event.get("choices", [{}])[0].get("delta", {}).get("content", "")
        if chunk:
            yield chunk


def estimate_num_tokens(text):
    """Approximate token count without requiring heavyweight tokenizer dependencies."""
    return max(1, len(re.findall(r"\w+|[^\w\s]", text)))


MUSIC_FEATURES = ["danceability", "energy", "speechiness", "acousticness", "valence", "tempo_norm"]
MOOD_AUDIO_RANGES = {
    "frustrated": {
        "danceability": (0.40, 0.58),
        "energy": (0.72, 0.94),
        "speechiness": (0.06, 0.16),
        "acousticness": (0.06, 0.28),
        "valence": (0.20, 0.44),
        "tempo_norm": (0.52, 0.74),
    },
    "motivated": {
        "danceability": (0.58, 0.78),
        "energy": (0.76, 0.96),
        "speechiness": (0.04, 0.13),
        "acousticness": (0.02, 0.18),
        "valence": (0.60, 0.84),
        "tempo_norm": (0.48, 0.68),
    },
    "excited": {
        "danceability": (0.68, 0.88),
        "energy": (0.80, 0.98),
        "speechiness": (0.04, 0.15),
        "acousticness": (0.01, 0.16),
        "valence": (0.74, 0.94),
        "tempo_norm": (0.56, 0.80),
    },
    "satisfied": {
        "danceability": (0.48, 0.68),
        "energy": (0.42, 0.64),
        "speechiness": (0.02, 0.08),
        "acousticness": (0.32, 0.58),
        "valence": (0.60, 0.84),
        "tempo_norm": (0.32, 0.52),
    },
    "tired": {
        "danceability": (0.24, 0.46),
        "energy": (0.14, 0.36),
        "speechiness": (0.02, 0.08),
        "acousticness": (0.62, 0.90),
        "valence": (0.28, 0.50),
        "tempo_norm": (0.22, 0.44),
    },
    "gloomy": {
        "danceability": (0.28, 0.48),
        "energy": (0.22, 0.46),
        "speechiness": (0.02, 0.08),
        "acousticness": (0.54, 0.84),
        "valence": (0.08, 0.30),
        "tempo_norm": (0.28, 0.48),
    },
}


def sample_mood_audio_profile(mood):
    return {
        feature: np.random.uniform(low, high)
        for feature, (low, high) in MOOD_AUDIO_RANGES[mood].items()
    }


def prepare_music_dataset(df):
    """Coerce audio columns to numeric values and add a normalized tempo feature."""
    df = df.copy()
    audio_columns = ["danceability", "energy", "speechiness", "acousticness", "valence", "tempo"]
    for column in audio_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df = df.dropna(subset=audio_columns + ["Song", "Performer", "spotify_track_id"])
    tempo_min = df["tempo"].min()
    tempo_max = df["tempo"].max()
    if tempo_max == tempo_min:
        df["tempo_norm"] = 0.5
    else:
        df["tempo_norm"] = (df["tempo"] - tempo_min) / (tempo_max - tempo_min)
    return df

# Function to create SQLite database and table if not exists
def create_database():
    conn = sqlite3.connect('user_data.db')
    c = conn.cursor()
    
    # Check if the users table exists
    c.execute('''SELECT count(name) FROM sqlite_master WHERE type='table' AND name='users' ''')
    if c.fetchone()[0] == 0:
        # Create the new users table
        c.execute('''CREATE TABLE users
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                     username TEXT NOT NULL, 
                     email TEXT NOT NULL, 
                     project_id TEXT NOT NULL,
                     image BLOB)''')
    
    # Check if the tasks table exists
    c.execute('''SELECT count(name) FROM sqlite_master WHERE type='table' AND name='tasks' ''')
    if c.fetchone()[0] == 0:
        # Create the new tasks table
        c.execute('''CREATE TABLE tasks
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     project_id TEXT NOT NULL,
                     task_description TEXT NOT NULL,
                     completed BOOLEAN NOT NULL DEFAULT 0,
                     completed_by TEXT)''')
    
    conn.commit()
    conn.close()

# Function to insert task into the database
def insert_task(project_id, task_description):
    conn = sqlite3.connect('user_data.db')
    c = conn.cursor()
    c.execute('''INSERT INTO tasks (project_id, task_description) VALUES (?, ?)''',
              (project_id, task_description))
    conn.commit()
    conn.close()

# Function to mark task as completed
def mark_task_as_completed(task_id, username):
    conn = sqlite3.connect('user_data.db')
    c = conn.cursor()
    c.execute('''UPDATE tasks SET completed = 1, completed_by = ? WHERE id = ?''',
              (username, task_id))
    conn.commit()
    conn.close()

# Function to delete task from the database
def delete_task(task_id):
    conn = sqlite3.connect('user_data.db')
    c = conn.cursor()
    c.execute('''DELETE FROM tasks WHERE id = ?''', (task_id,))
    conn.commit()
    conn.close()

# Function to delete project records from both tables
def delete_project(project_id):
    conn = sqlite3.connect('user_data.db')
    c = conn.cursor()
    c.execute('''DELETE FROM tasks WHERE project_id = ?''', (project_id,))
    c.execute('''DELETE FROM users WHERE project_id = ?''', (project_id,))
    conn.commit()
    conn.close()

# Function to retrieve tasks from the database
def get_tasks_by_project_id(project_id):
    conn = sqlite3.connect('user_data.db')
    c = conn.cursor()
    c.execute('''SELECT * FROM tasks WHERE project_id = ?''', (project_id,))
    tasks = c.fetchall()
    conn.close()
    return tasks

# Function to retrieve completed and total tasks
def get_completed_and_total_tasks(project_id):
    conn = sqlite3.connect('user_data.db')
    c = conn.cursor()
    c.execute('''SELECT SUM(completed), COUNT(*) FROM tasks WHERE project_id = ?''', (project_id,))
    completed, total = c.fetchone()
    conn.close()
    return completed, total

# Function to retrieve user contributions
def get_user_contributions(project_id):
    conn = sqlite3.connect('user_data.db')
    c = conn.cursor()
    c.execute('''SELECT completed_by, COUNT(*) FROM tasks WHERE project_id = ? AND completed = 1 GROUP BY completed_by''', (project_id,))
    user_contributions = c.fetchall()
    conn.close()
    return user_contributions

# Function to insert user data into the database
def insert_user_data(username, email, project_id, image):
    conn = sqlite3.connect('user_data.db')
    c = conn.cursor()
    c.execute('''INSERT INTO users (username, email, project_id, image) VALUES (?, ?, ?, ?)''',
              (username, email, project_id, image))
    conn.commit()
    conn.close()

# Function to retrieve user data based on project ID and username
def get_user_by_project_id_and_username(project_id, username):
    conn = sqlite3.connect('user_data.db')
    c = conn.cursor()
    c.execute('''SELECT * FROM users WHERE project_id = ? AND username = ?''', (project_id, username))
    data = c.fetchone()
    conn.close()
    return data

# Function to delete user record based on project ID and username
def delete_user_record(project_id, username):
    conn = sqlite3.connect('user_data.db')
    c = conn.cursor()
    c.execute('''DELETE FROM users WHERE project_id = ? AND username = ?''', (project_id, username))
    conn.commit()
    conn.close()

# Function to retrieve user data based on project ID
def get_users_by_project_id(project_id):
    conn = sqlite3.connect('user_data.db')
    c = conn.cursor()
    c.execute('''SELECT * FROM users WHERE project_id = ?''', (project_id,))
    data = c.fetchall()
    conn.close()
    return data

def parse_task_lines(response_content):
    """Extract clean task rows from a model-generated project breakdown."""
    task_lines = []
    fallback_lines = []
    task_pattern = re.compile(r"^\s*(?:[-*]\s*)?(?:\d+[\).\:-]\s*|Step\s+\d+[\).\:-]\s*)(.+)$", re.IGNORECASE)
    bullet_pattern = re.compile(r"^\s*[-*]\s+(.+)$")

    for raw_line in str(response_content).splitlines():
        line = raw_line.strip()
        if not line or line.startswith("```") or line.lower() in {"tasks:", "task list:", "output:"}:
            continue

        numbered_match = task_pattern.match(line)
        bullet_match = bullet_pattern.match(line)

        if numbered_match:
            task_text = numbered_match.group(1).strip()
            task_number = len(task_lines) + 1
            task_lines.append(f"{task_number}. {task_text}")
        elif bullet_match:
            task_text = bullet_match.group(1).strip()
            task_number = len(task_lines) + 1
            task_lines.append(f"{task_number}. {task_text}")
        else:
            fallback_lines.append(line)

    if not task_lines:
        task_lines = [
            f"{index}. {line}"
            for index, line in enumerate(fallback_lines, start=1)
            if len(line) > 2
        ]

    cleaned_tasks = []
    seen = set()
    for task in task_lines:
        task = re.sub(r"\s+", " ", task).strip()
        if task and task not in seen:
            cleaned_tasks.append(task)
            seen.add(task)

    return cleaned_tasks

# Main Streamlit app
def main():
    # Create SQLite database if it doesn't exist
    create_database()
    # Set page title and navigation
    st.set_page_config(page_title="WorkPod", layout="wide", initial_sidebar_state="expanded", page_icon = "./WP.png")
    # Page navigation
    with st.sidebar:

        st.image("./workpodtitle.png", width="stretch")
        st.image("./dolphinwordcloud.png", width="stretch")
        page = st.radio("", ["Registration", "Login", "Arctic", "OneDash", "Oasis"])


    if page == "Registration":
        st.markdown(
         f"""
         <style>
         .stApp {{
             background-image: url("https://images.unsplash.com/photo-1634017839464-5c339ebe3cb4?q=80&w=1935&auto=format&fit=crop&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D");
             background-attachment: fixed;
             background-size: cover
         }}
         </style>
         """,
         unsafe_allow_html=True
        )
        st.title("Register Your Account")

        # Display form for user input
        project_id = st.text_input("Enter Project ID:")
        username = st.text_input("Enter your username:")
        email = st.text_input("Enter your email:")
        uploaded_image = st.file_uploader("Upload Profile Image", type=['jpg', 'jpeg', 'png'])

        # Save user data to database upon form submission
        if st.button("Submit"):
            if project_id and username and email:
                existing_user = get_user_by_project_id_and_username(project_id, username)
                if existing_user is None:
                    if uploaded_image is not None:
                        image_bytes = uploaded_image.read()
                        insert_user_data(username, email, project_id, image_bytes)
                        st.success("You have successfully registered! Please head to Login.")
                    else:
                        st.error("Please upload a profile image.")
                else:
                    st.success("You are already registered!")
            else:
                st.error("Please fill in all the fields.")

    elif page == "Login":
        st.markdown(
         f"""
         <style>
         .stApp {{
             background-image: url("https://images.unsplash.com/photo-1634017839464-5c339ebe3cb4?q=80&w=1935&auto=format&fit=crop&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D");
             background-attachment: fixed;
             background-size: cover
         }}
         </style>
         """,
         unsafe_allow_html=True
        )
        st.title("Login")

        # Display form for user input
        project_id = st.text_input("Enter Project ID:")
        username = st.text_input("Enter your username:")

        # Login button
        if st.button("Login"):
            if project_id and username:
                existing_user = get_user_by_project_id_and_username(project_id, username)
                if existing_user is not None:
                    st.session_state.project_id = project_id
                    st.session_state.username = username
                    st.success("Login successful! Please continue.")
                else:
                    st.error("Invalid project ID or username.")
            else:
                st.error("Please fill in all the fields.")
    

    elif page == "Arctic":
        st.title("Let's Break The Ice!")
        username = st.session_state.get("username")
        with st.sidebar:
            model_provider = st.selectbox(
                "Model Provider",
                ["Groq - Llama 3.1 8B Instant", "Snowflake Arctic via Replicate (legacy)"],
            )
            use_groq = model_provider.startswith("Groq")
            replicate_api = ""
            groq_api = ""
            groq_model = DEFAULT_GROQ_MODEL
            if use_groq:
                groq_model = st.text_input("Groq model", value=DEFAULT_GROQ_MODEL)
                if 'GROQ_API_KEY' in st.secrets:
                    groq_api = st.secrets['GROQ_API_KEY']
                    st.caption("Using Groq API key from Streamlit secrets.")
                else:
                    groq_api = st.text_input('Enter Groq API key:', type='password')
                    if not groq_api:
                        st.warning('Please enter your Groq API key.', icon='⚠️')
                os.environ['GROQ_API_KEY'] = groq_api
            else:
                if 'REPLICATE_API_TOKEN' in st.secrets:
                    replicate_api = st.secrets['REPLICATE_API_TOKEN']
                else:
                    replicate_api = st.text_input('Enter Replicate API token:', type='password')
                    if not (replicate_api.startswith('r8_') and len(replicate_api)==40):
                        st.warning('Please enter your Replicate API token.', icon='⚠️')
                        st.markdown("**Don't have an API token?** Head over to [Replicate](https://replicate.com) to sign up for one.")
        
                os.environ['REPLICATE_API_TOKEN'] = replicate_api
            st.subheader("Model Creativity Control")
            temperature = st.sidebar.slider('temperature', min_value=0.2, max_value=1.5, value=0.6, step=0.1)
    
        # Store LLM-generated responses
        if "messages" not in st.session_state.keys():
            if username:
                st.session_state.messages = [{"role": "assistant", "content": f"Hi {username}! I'm WorkPod AI, now running on Llama 3.1 through Groq. I heard you are working on a special project, and I can help break it down into clear steps."}]
            else:
                st.session_state.messages = [{"role": "assistant", "content": f"Hi! I'm WorkPod AI, now running on Llama 3.1 through Groq. I heard you are working on a special project, and I can help break it down into clear steps."}]
    
        # Display or clear chat messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"], avatar=icons[message["role"]]):
                st.write(message["content"])
    
        def clear_chat_history():
            if username:
                st.session_state.messages = [{"role": "assistant", "content": f"Hi {username}! I'm WorkPod AI, now running on Llama 3.1 through Groq. I heard you are working on a special project, and I can help break it down into clear steps."}]
            else:
                st.session_state.messages = [{"role": "assistant", "content": f"Hi! I'm WorkPod AI, now running on Llama 3.1 through Groq. I heard you are working on a special project, and I can help break it down into clear steps."}]
            
        st.sidebar.button('Clear chat history', on_click=clear_chat_history)
    
        # Function for generating Snowflake Arctic response kept as the legacy path
        def generate_snowflake_arctic_response():
            prompt = []
            for dict_message in st.session_state.messages:
                if dict_message["role"] == "user":
                    prompt.append("<|im_start|>user\n" + dict_message["content"] + "<|im_end|>")
                else:
                    prompt.append("<|im_start|>assistant\n" + dict_message["content"] + "<|im_end|>")
            
            prompt.append("<|im_start|>assistant")
            prompt.append("Cool! ")
            prompt_str = "\n".join(prompt)
            
            if estimate_num_tokens(prompt_str) >= 3072:
                st.error("Conversation length too long. Please keep it under 3072 tokens.")
                st.button('Clear chat history', on_click=clear_chat_history, key="clear_chat_history")
                st.stop()
        
            for event in replicate.stream("snowflake/snowflake-arctic-instruct",
                                   input={"prompt": prompt_str,
                                          "prompt_template": r"{prompt}",
                                          "temperature": temperature,
                                          "top_p": 0.9,
                                          }):
                yield str(event)

        def generate_groq_project_response():
            groq_messages = [
                {
                    "role": "system",
                    "content": (
                        "Purpose: Convert a project idea into dashboard-ready tasks for WorkPod. "
                        "Action: Break the project into 5 to 8 concrete implementation tasks. "
                        "Output: Return only a numbered list. Each line must follow this exact format: "
                        "1. Task title - expected time: X days. "
                        "Do not include greetings, summaries, markdown headings, blank lines, or extra notes."
                    ),
                },
            ] + st.session_state.messages
            return stream_groq_chat(groq_messages, api_key=groq_api, model=groq_model, temperature=temperature)
        
        # User-provided prompt
        if prompt := st.chat_input(disabled=(not use_groq and not replicate_api) or (use_groq and not groq_api)):
            st.session_state.messages.append({"role": "user", "content": prompt + " Break this project into WorkPod dashboard tasks. Return only the numbered task list in the required format."})
            with st.chat_message("user", avatar="🐬"):
                st.write(prompt)

        # Generate a new response if last message is not from assistant
        if st.session_state.messages[-1]["role"] != "assistant":
            with st.chat_message("assistant", avatar=icons["assistant"] if use_groq else "./Snowflake_Logomark_blue.svg"):
                response = generate_groq_project_response() if use_groq else generate_snowflake_arctic_response()
                full_response = st.write_stream(response)
            message = {"role": "assistant", "content": full_response}
            filtered_lines = parse_task_lines(full_response)
            st.session_state.messages.append(message)
            st.session_state.tasks = filtered_lines
            project_id = st.session_state.get("project_id")
            if project_id:
                if filtered_lines:
                    for task_description in filtered_lines:
                        insert_task(project_id, task_description)
                    st.success("Tasks pushed to OneDash!")
                else:
                    st.warning("I could not find task lines in the model response. Please try again with a little more project detail.")
            else:
                st.error("Project ID not found. Please log in first.")

    elif page == "OneDash":
        st.title("OneDash - Project Dashboard :bar_chart:")
        st.header("",divider="rainbow")
        project_id = st.session_state.get("project_id")
        username = st.session_state.get("username")
        if project_id:
            st.write(f"You are currently working on Project ID: {project_id}")
    
            # Exit project button
            if st.button("Exit Project", key="exit_button"):
                if username:
                    delete_user_record(project_id, username)
                    st.success(f"You have exited Project ID '{project_id}'. Your record has been removed.")
                else:
                    st.write("No username. Please log in first.")
    
            # Display users with the same project ID
            st.sidebar.header(":grey-background[Project Members]")
            project_users = get_users_by_project_id(project_id)
            for user in project_users:
                st.sidebar.markdown(f"Username: {user[1]}")
                st.sidebar.markdown(f"Email: {user[2]}")
                if user[4] is not None:
                    # Display uploaded image
                    image = Image.open(io.BytesIO(user[4]))
                    st.sidebar.image(image, width="stretch", caption=user[1])
        
            tasks = get_tasks_by_project_id(project_id)
            if tasks:
                completed, total = get_completed_and_total_tasks(project_id)
                if completed == total:
                    st.subheader("Congratulations! You've successfully completed your project!")
                    if st.button("Delete Project", key="delete_project_button"):
                        delete_project(project_id)
                        st.success(f"Project '{project_id}' has been successfully deleted. Hope to see you again!")
                completed_percentage = int((completed / total) * 100)
                st.subheader("Progress Report")
                st.write(f"Completed Tasks: {completed} / {total}")
                st.progress(completed_percentage, "Progress of Project Completion")

                user_contributions = get_user_contributions(project_id)
                user_contributions_df = pd.DataFrame(user_contributions, columns=["User", "Completed Tasks"])
                fig = px.pie(user_contributions_df, names="User", values="Completed Tasks", title="User Contributions")
                fig.update_traces(textposition='inside', textinfo='percent+label', textfont_color='white')
                st.plotly_chart(fig)
            
                st.subheader("Tasks from WorkPod AI as To-Dos:")
                for task in tasks:
                    task_id, _, task_description, completed, completed_by = task
                    task_description = (task_description or "").strip()
                    if not task_description:
                        continue
                    if task_description[:1].isdigit():
                        st.write(f":blue[{task_description}]")
                    else:
                        st.write(f"- {task_description}")
                    # Checkbox for marking task as completed
                    if not completed:
                        completed = st.checkbox("Completed", key=f"completed_{task_id}")
                        if completed:
                            mark_task_as_completed(task_id, username)
                    else:
                        st.markdown(f":green[Task completed by:] {completed_by}")
                    # Button to delete task
                    if st.button("Delete", key=f"delete_{task_id}"):
                        delete_task(task_id)
                        st.success("Task deleted!")
            else:
                st.info("No tasks available.")
        else:
            st.info("Please log in first")

    elif page == "Oasis":
        st.title("Oasis - Music for your Mood :musical_note:")
        st.header("",divider="rainbow")
        username = st.session_state.get("username")
        with st.sidebar:
            model_provider = st.selectbox(
                "Model Provider",
                ["Groq - Llama 3.1 8B Instant", "Snowflake Arctic via Replicate (legacy)"],
                key="oasis_model_provider",
            )
            use_groq = model_provider.startswith("Groq")
            replicate_api = ""
            groq_api = ""
            groq_model = DEFAULT_GROQ_MODEL
            if use_groq:
                groq_model = st.text_input("Groq model", value=DEFAULT_GROQ_MODEL, key="oasis_groq_model")
                if 'GROQ_API_KEY' in st.secrets:
                    groq_api = st.secrets['GROQ_API_KEY']
                    st.caption("Using Groq API key from Streamlit secrets.")
                else:
                    groq_api = st.text_input('Enter Groq API key:', type='password', key="oasis_groq_api_key")
                    if not groq_api:
                        st.warning('Please enter your Groq API key.', icon='⚠️')
                os.environ['GROQ_API_KEY'] = groq_api
            else:
                if 'REPLICATE_API_TOKEN' in st.secrets:
                    replicate_api = st.secrets['REPLICATE_API_TOKEN']
                else:
                    replicate_api = st.text_input('Enter Replicate API token:', type='password')
                    if not (replicate_api.startswith('r8_') and len(replicate_api)==40):
                        st.warning('Please enter your Replicate API token.', icon='⚠️')
                        st.markdown("**Don't have an API token?** Head over to [Replicate](https://replicate.com) to sign up for one.")
        
                os.environ['REPLICATE_API_TOKEN'] = replicate_api

        if username:
            st.write(f"Hello {username}. How are you feeling today?")
        else:
            st.write("Hello. How are you feeling today?")
        
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        with col1:
            with stylable_container(key="but1", css_styles="""
                button {
                    background-color: firebrick;
                    border-radius: 15px;
                    color: white;
                    border: 2px solid indianred;
                }"""):
                red_clicked = st.button("Frustrated", key="but1")
        with col2:
            with stylable_container(key="but2", css_styles="""
                button {
                    background-color: chocolate;
                    border-radius: 15px;
                    color: white;
                    border: 2px solid sandybrown;
                }"""):
                orange_clicked = st.button("Motivated", key="but2")
        with col3:
            with stylable_container(key="but3", css_styles="""
                button {
                    background-color: goldenrod;
                    border-radius: 15px;
                    color: white;
                    border: 2px solid khaki;
                }"""):
                yellow_clicked = st.button("Excited", key="but3")
        with col4:
            with stylable_container(key="but4", css_styles="""
                button {
                    background-color: forestgreen;
                    border-radius: 15px;
                    color: white;
                    border: 2px solid palegreen;
                }"""):
                green_clicked = st.button("Satisfied", key="but4")
        with col5:
            with stylable_container(key="but5", css_styles="""
                button {
                    background-color: darkblue;
                    border-radius: 15px;
                    color: white;
                    border: 2px solid royalblue;
                }"""):
                blue_clicked = st.button("Tired", key="but5")
        with col6:
            with stylable_container(key="but6", css_styles="""
                button {
                    background-color: indigo;
                    border-radius: 15px;
                    color: white;
                    border: 2px solid blueviolet;
                }"""):
                purple_clicked = st.button("Gloomy", key="but6")

        if "musicrequest" not in st.session_state.keys():
            st.session_state.musicrequest = [{"role": "assistant", "content": "Let's vibe with some music!"}]

        def clear_chat_history():
            st.session_state.musicrequest = [{"role": "assistant", "content": "Let's vibe with some music!"}]
        
        # Function for generating Snowflake Arctic response kept as the legacy path
        def generate_snowflake_arctic_response():
            prompt = []
            for dict_message in st.session_state.musicrequest:
                if dict_message["role"] == "user":
                    prompt.append("<|im_start|>user\n" + dict_message["content"] + "<|im_end|>")
                else:
                    prompt.append("<|im_start|>assistant\n" + dict_message["content"] + "<|im_end|>")
            
            prompt.append("<|im_start|>assistant")
            prompt_str = "\n".join(prompt)
            
            if estimate_num_tokens(prompt_str) >= 3072:
                st.error("Conversation length too long. Please keep it under 3072 tokens.")
                st.button('Clear chat history', on_click=clear_chat_history, key="clear_chat_history")
                st.stop()
        
            for event in replicate.stream("snowflake/snowflake-arctic-instruct",
                                   input={"prompt": prompt_str,
                                          "prompt_template": r"{prompt}",
                                          "temperature": 0.5,
                                          "top_p": 0.9,
                                          }):
                yield str(event)

        def generate_groq_music_response():
            groq_messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a music therapy feature assistant. Return a short answer that includes "
                        "exactly one Python-style array with six numbers between 0 and 1 in this order: "
                        "danceability, energy, speechiness, acousticness, valence, tempo. "
                        "Do not include any other bracketed list."
                    ),
                },
            ] + st.session_state.musicrequest
            return stream_groq_chat(groq_messages, api_key=groq_api, model=groq_model, temperature=0.5)

        url = "./musicdata.csv"
        df = prepare_music_dataset(pd.read_csv(url))

        def make_clickable(val):
            # target _blank to open new window
            return '<a target="_blank" href="{}">{}</a>'.format(val, val)
        
        def get_recommendations(df, profile, amount):
            target = pd.Series(profile, dtype=float)
            weights = pd.Series({
                "danceability": 1.0,
                "energy": 1.25,
                "speechiness": 0.55,
                "acousticness": 1.1,
                "valence": 1.35,
                "tempo_norm": 0.8,
            })
            distances = ((df[MUSIC_FEATURES] - target[MUSIC_FEATURES]).abs() * weights[MUSIC_FEATURES]).sum(axis=1)
            res = df.assign(distance=distances).sort_values('distance')
            res['spotify_track_id'] = res['spotify_track_id'].apply(make_clickable)
            columns=['Song', 'Performer', 'spotify_track_id']
            return res[columns][:amount]
        
        mood = ""
        selected_mood = ""
        reply = ""
        
        if red_clicked:
            clear_chat_history()
            selected_mood = "frustrated"
            mood = "I am feeling frustrated and annoyed."
            reply = "Oh! 😯 Well, music can be a great outlet for such emotions. I've got some songs for you that may uplift your mood."
        elif orange_clicked:
            clear_chat_history()
            selected_mood = "motivated"
            mood = "I am feeling motivated to work harder."
            reply = "Nice! 😎 I've got you covered! Get ready to be motivated through these powerful songs!"
        elif yellow_clicked:
            clear_chat_history()
            selected_mood = "excited"
            mood = "I am feeling excited!"
            reply = "Me too! 😃 Let's channel that excitement with some upbeat tunes! Get ready for an electrifying playlist!"
        elif green_clicked:
            clear_chat_history()
            selected_mood = "satisfied"
            mood = "I am feeling satisfied and content."
            reply = "That's great to hear. 😊 How about we enhance that feeling of contentment with some nice songs?"
        elif blue_clicked:
            clear_chat_history()
            selected_mood = "tired"
            mood = "I am feeling tired and need to relax."
            reply = "It sounds like you've had a busy day! 😓 I've got some soothing tunes that will help you relax and rejuvenate."
        elif purple_clicked:
            clear_chat_history()
            selected_mood = "gloomy"
            mood = "I am feeling gloomy."
            reply = "Oh my, I've been there too 😟, but don't worry, that feeling will fade away soon. Let it flow out through these tunes."
        if prompt:=mood:
            st.session_state.musicrequest.append({"role": "user", "content": prompt + " You are going to perform music therapy. Your task is to list the normalised values (0-1) for danceability, energy, speechiness, acousticness, valence, and tempo for a song that best matches with my given mood. It is compulsory to include a list of the 6 numbers arranged in an array. The list is mandatory so always generate it. Keep your response short."})
            st.session_state.selected_oasis_mood = selected_mood

        # Generate a new response if last message is not from assistant
        if st.session_state.musicrequest[-1]["role"] != "assistant":
            st.write("")
            st.write(reply)
            selected_mood = st.session_state.get("selected_oasis_mood", selected_mood)
            recdf = get_recommendations(df, sample_mood_audio_profile(selected_mood), 10)
            recdf.reset_index(drop=True, inplace=True)
            st.subheader("Recommended Songs")
            rec = st.write(recdf.to_html(escape = False), unsafe_allow_html = True)
            if use_groq and not groq_api:
                st.session_state.musicrequest.append({"role": "assistant", "content": "Recommendations generated from the local music dataset."})
                st.caption("Add a Groq API key in the sidebar for an LLM-generated mood summary.")
                st.stop()
            response = generate_groq_music_response() if use_groq else generate_snowflake_arctic_response()
            full_response = ''
            for i in response:
                full_response += str(i)
            message = {"role": "assistant", "content": full_response}
            match = re.search(r'\[(.*?)\]', full_response)
            st.session_state.musicrequest.append(message)
            if match:
                extracted_array = re.findall(r'0?\.\d+|1(?:\.0+)?|0(?:\.0+)?', match.group(1))
                if len(extracted_array) >= 6:
                    st.caption(f"LLM mood vector: [{', '.join(extracted_array[:6])}]")
            
if __name__ == "__main__":
    main()

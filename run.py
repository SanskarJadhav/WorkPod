import streamlit as st
from streamlit_extras.stylable_container import stylable_container
import sqlite3
import requests
from PIL import Image
import io
import replicate
import os
import re
from transformers import AutoTokenizer
import plotly.express as px
import pandas as pd
import numpy as np

# Set assistant icon to Snowflake logo
icons = {"assistant": "./Snowflake_Logomark_blue.svg", "user": "🐬"}

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

# Function to extract tasks from Arctic response
def extract_tasks_from_response(response):
    tasks = []
    for message in response:
        if message["role"] == "assistant":
            # Extract the list of tasks from the assistant's message
            response_content = message["content"]
            tasks = [task.strip() for task in response_content.split('\n') if task.strip()]
    return tasks

# Main Streamlit app
def main():
    # Create SQLite database if it doesn't exist
    create_database()
    # Set page title and navigation
    st.set_page_config(page_title="WorkPod", layout="wide", initial_sidebar_state="expanded", page_icon = "https://raw.githubusercontent.com/SanskarJadhav/profileweb/main/WP.png")
    # Page navigation
    with st.sidebar:

        st.image("https://raw.githubusercontent.com/SanskarJadhav/profileweb/main/workpodtitle.png", use_column_width=True)
        st.image("https://raw.githubusercontent.com/SanskarJadhav/profileweb/main/dolphinwordcloud.png", use_column_width=True)
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
                st.session_state.messages = [{"role": "assistant", "content": f"Hi {username}! I'm Arctic, and yeah I'm pretty cool ;) I heard you are working on some special project. I'm very excited to hear more about it! I could even help break down the project for you."}]
            else:
                st.session_state.messages = [{"role": "assistant", "content": f"Hi! I'm Arctic, and yeah I'm pretty cool ;) I heard you are working on some special project. I'm very excited to hear more about it! I could even help break down the project for you."}]
    
        # Display or clear chat messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"], avatar=icons[message["role"]]):
                st.write(message["content"])
    
        def clear_chat_history():
            if username:
                st.session_state.messages = [{"role": "assistant", "content": f"Hi {username}! I'm Arctic, and yeah I'm pretty cool ;) I heard you are working on some special project. I'm very excited to hear more about it! I could even help break down the project for you."}]
            else:
                st.session_state.messages = [{"role": "assistant", "content": f"Hi! I'm Arctic, and yeah I'm pretty cool ;) I heard you are working on some special project. I'm very excited to hear more about it! I could even help break down the project for you."}]
            
        st.sidebar.button('Clear chat history', on_click=clear_chat_history)
    
        @st.cache_resource(show_spinner=False)
        def get_tokenizer():
            return AutoTokenizer.from_pretrained("huggyllama/llama-7b")
    
        def get_num_tokens(prompt):
            """Get the number of tokens in a given prompt"""
            tokenizer = get_tokenizer()
            tokens = tokenizer.tokenize(prompt)
            return len(tokens)
        
        # Function for generating Snowflake Arctic response
        def generate_arctic_response():
            prompt = []
            for dict_message in st.session_state.messages:
                if dict_message["role"] == "user":
                    prompt.append("<|im_start|>user\n" + dict_message["content"] + "<|im_end|>")
                else:
                    prompt.append("<|im_start|>assistant\n" + dict_message["content"] + "<|im_end|>")
            
            prompt.append("<|im_start|>assistant")
            prompt.append("Cool! ")
            prompt_str = "\n".join(prompt)
            
            if get_num_tokens(prompt_str) >= 3072:
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
        
        # User-provided prompt
        if prompt := st.chat_input(disabled=not replicate_api):
            st.session_state.messages.append({"role": "user", "content": prompt + " Could you help me by breaking down this project into steps as bullet points. Highlight what each step will be and expected time for completion of each. Not too long."})
            with st.chat_message("user", avatar="🐬"):
                st.write(prompt)

        # Generate a new response if last message is not from assistant
        if st.session_state.messages[-1]["role"] != "assistant":
            with st.chat_message("assistant", avatar="./Snowflake_Logomark_blue.svg"):
                response = generate_arctic_response()
                full_response = st.write_stream(response)
            message = {"role": "assistant", "content": full_response}
            filtered_lines = []
            # Flag to indicate when to start saving lines
            save_lines = False
            for line in str(full_response).splitlines():
                # Check if the line starts with "1."
                if line.strip().startswith("1."):
                    save_lines = True
                if save_lines:
                    cleaned_line = line.strip().lstrip("* ")
                    filtered_lines.append(cleaned_line)
            st.session_state.messages.append(message)
            st.session_state.tasks = filtered_lines
            project_id = st.session_state.get("project_id")
            if project_id:
                for task_description in filtered_lines:
                    insert_task(project_id, task_description)
                st.success("Tasks pushed to OneDash!")
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
                    st.sidebar.image(image, use_column_width=True, caption=user[1])

            # Display progress bar chart for completed tasks percentage out of total tasks
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
    
            # Display user contributions pie chart
            user_contributions = get_user_contributions(project_id)
            user_contributions_df = pd.DataFrame(user_contributions, columns=["User", "Completed Tasks"])
            fig = px.pie(user_contributions_df, names="User", values="Completed Tasks", title="User Contributions")
            fig.update_traces(textposition='inside', textinfo='percent+label', textfont_color='white')
            st.plotly_chart(fig)
        
            tasks = get_tasks_by_project_id(project_id)
            if tasks:
                st.subheader("Tasks from Arctic as To-Dos:")
                for task in tasks:
                    task_id, _, task_description, completed, completed_by = task
                    if task_description[0].isdigit():
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
            if 'REPLICATE_API_TOKEN' in st.secrets:
                replicate_api = st.secrets['REPLICATE_API_TOKEN']
            else:
                replicate_api = st.text_input('Enter Replicate API token:', type='password')
                if not (replicate_api.startswith('r8_') and len(replicate_api)==40):
                    st.warning('Please enter your Replicate API token.', icon='⚠️')
                    st.markdown("**Don't have an API token?** Head over to [Replicate](https://replicate.com) to sign up for one.")
    
            os.environ['REPLICATE_API_TOKEN'] = replicate_api
        
        st.write(f"Hello {username}. How are we feeling today?")
        
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
        
        @st.cache_resource(show_spinner=False)
        def get_tokenizer():
            return AutoTokenizer.from_pretrained("huggyllama/llama-7b")
    
        def get_num_tokens(prompt):
            """Get the number of tokens in a given prompt"""
            tokenizer = get_tokenizer()
            tokens = tokenizer.tokenize(prompt)
            return len(tokens)
        
        # Function for generating Snowflake Arctic response
        def generate_arctic_response():
            prompt = []
            for dict_message in st.session_state.musicrequest:
                if dict_message["role"] == "user":
                    prompt.append("<|im_start|>user\n" + dict_message["content"] + "<|im_end|>")
                else:
                    prompt.append("<|im_start|>assistant\n" + dict_message["content"] + "<|im_end|>")
            
            prompt.append("<|im_start|>assistant")
            prompt_str = "\n".join(prompt)
            
            if get_num_tokens(prompt_str) >= 3072:
                st.error("Conversation length too long. Please keep it under 3072 tokens.")
                st.button('Clear chat history', on_click=clear_chat_history, key="clear_chat_history")
                st.stop()
        
            for event in replicate.stream("snowflake/snowflake-arctic-instruct",
                                   input={"prompt": prompt_str,
                                          "prompt_template": r"{prompt}",
                                          "temperature": 0.4,
                                          "top_p": 0.9,
                                          }):
                yield str(event)

        url = "https://raw.githubusercontent.com/SanskarJadhav/profileweb/main/musicdata.csv"
        df = pd.read_csv(url)

        def make_clickable(val):
            # target _blank to open new window
            return '<a target="_blank" href="{}">{}</a>'.format(val, val)
        
        def get_recommendations(df, input, amount):
            distances = []
            for r_song in df.values:
                dist = 0
                dist += np.absolute(float(input[0]) - float(r_song[4]))
                dist += np.absolute(float(input[1]) - float(r_song[5]))
                dist += np.absolute(float(input[2]) - float(r_song[6]))
                dist += np.absolute(float(input[3]) - float(r_song[7]))
                dist += np.absolute(float(input[4]) - float(r_song[8]))
                dist += np.absolute(float(input[5]) - float(r_song[9]))
                distances.append(dist)
            df['distance'] = distances
            res = df.sort_values('distance')
            res['spotify_track_id'] = res['spotify_track_id'].apply(make_clickable)
            columns=['Song', 'Performer', 'spotify_track_id']
            return res[columns][:amount]
        
        mood = ""
        
        if red_clicked:
            clear_chat_history()
            mood = "I am feeling frustrated."
        elif orange_clicked:
            clear_chat_history()
            mood = "I am feeling motivated to work harder."
        elif yellow_clicked:
            clear_chat_history()
            mood = "I am feeling excited!"
        elif green_clicked:
            clear_chat_history()
            mood = "I am feeling satisfied and content."
        elif blue_clicked:
            clear_chat_history()
            mood = "I am feeling tired and worked out."
        elif purple_clicked:
            clear_chat_history()
            mood = "I am feeling gloomy."

        if prompt:=mood:
            st.session_state.musicrequest.append({"role": "user", "content": prompt + " You are going to perform music therapy. Your task is to list the normalised values (0-1) for danceability, energy, speechiness, acousticness, valence, and tempo for a song that best matches with my given mood. It is compulsory to include a list of the 6 numbers arranged in an array. The list is mandatory so always generate it."})

        # Generate a new response if last message is not from assistant
        if st.session_state.musicrequest[-1]["role"] != "assistant":
            response = generate_arctic_response()
            chunks = []
            while True:
                chunk = response.read(4096)  # Read 4KB chunks (adjust as needed)
                if not chunk:
                    break
                chunks.append(chunk)
            # Concatenate the chunks to form the full response
            full_response = b''.join(chunks)
            message = {"role": "assistant", "content": full_response}
            match = re.search(r'\[(.*?)\]', full_response)
            if match:
                extracted_array = match.group(1).split(', ')
            st.session_state.musicrequest.append(message)
            recdf = get_recommendations(df, extracted_array, 10)
            recdf.reset_index(drop=True, inplace=True)
            st.subheader("Recommended Songs")
            rec = st.write(recdf.to_html(escape = False), unsafe_allow_html = True)
            
if __name__ == "__main__":
    main()

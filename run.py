import streamlit as st
import sqlite3
import requests
from PIL import Image
import io
import replicate
import os
import re
from transformers import AutoTokenizer

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
        conn.commit()
    
    conn.close()

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
        page = st.radio("", ["Registration", "Login", "Arctic", "OneDash"])


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

        # Image upload
        uploaded_image = st.file_uploader("Upload Profile Image", type=['jpg', 'jpeg', 'png'])

        # Save user data to database upon form submission
        if st.button("Submit"):
            if project_id and username and email:
                existing_user = get_user_by_project_id_and_username(project_id, username)
                if existing_user is None:
                    if uploaded_image is not None:
                        # Convert uploaded image to bytes
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
        st.title("Arctic LLM Chatbot")
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
            st.session_state.messages = [{"role": "assistant", "content": f"Hi {username}! I'm Arctic, and yeah I'm pretty cool ;) I heard you are working on some special project. I'm very excited to hear more about it! I could even help break down the project for you."}]
    
        # Display or clear chat messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"], avatar=icons[message["role"]]):
                st.write(message["content"])
    
        def clear_chat_history():
            st.session_state.messages = [{"role": "assistant", "content": f"Hi {username}! I'm Arctic, and yeah I'm pretty cool ;) I heard you are working on some special project. I'm very excited to hear more about it! I could even help break down the project for you."}]
            
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
            st.session_state.messages.append({"role": "user", "content": prompt + " Could you help me by breaking down this project into steps. Just highlight what each step will be and expected time for completion of each."})
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
                    cleaned_line = line.lstrip("*")
                    filtered_lines.append(cleaned_line)
            tasks = filtered_lines
            st.session_state.messages.append(message)
            st.write("")
            st.write(tasks[:3])
                            
    # OneDash section
    elif page == "OneDash":
        st.title("OneDash - Project Dashboard")
        st.header("",divider="rainbow")
    
        # Display user's project ID
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
    
            # Display tasks from Arctic as to-dos
            if hasattr(st.session_state, 'onedash_tasks') and st.session_state.onedash_tasks:
                st.subheader("Tasks from Arctic as To-Dos:")
                for i, task in enumerate(st.session_state.onedash_tasks):
                    st.write(f"- To-Do {i+1}: {task}")
    

if __name__ == "__main__":
    main()

import streamlit as st
from PIL import Image

# Function to display the active users
def display_active_users(username, image):
    with st.sidebar:
        st.header("Active Users")
        if image:
            st.image(image, caption=username)
        else:
            st.write(f"{username}")

# Main function
def main():
    st.title("User Profile")
    username = st.text_input("Enter your username:", placeholder="Username")
    uploaded_file = st.file_uploader("Upload your profile picture:", type=["png", "jpg", "jpeg"])

    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        display_active_users(username, image)
    else:
        display_active_users(username, None)

if __name__ == "__main__":
    main()

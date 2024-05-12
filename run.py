import streamlit as st
import sqlite3
from PIL import Image
import io

# Function to create SQLite database and table
def create_database():
    conn = sqlite3.connect('user_data.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                 username TEXT NOT NULL, 
                 email TEXT NOT NULL, 
                 image BLOB)''')
    conn.commit()
    conn.close()

# Function to insert user data into the database
def insert_user_data(username, email, image):
    conn = sqlite3.connect('user_data.db')
    c = conn.cursor()
    c.execute('''INSERT INTO users (username, email, image) VALUES (?, ?, ?)''',
              (username, email, image))
    conn.commit()
    conn.close()

# Function to retrieve user data from the database
def get_user_data():
    conn = sqlite3.connect('user_data.db')
    c = conn.cursor()
    c.execute('''SELECT * FROM users''')
    data = c.fetchall()
    conn.close()
    return data

# Main Streamlit app
def main():
    st.title("User Profile Image Upload")

    # Create SQLite database if it doesn't exist
    create_database()

    # Display form for user input
    username = st.text_input("Enter your username:")
    email = st.text_input("Enter your email:")

    # Image upload
    uploaded_image = st.file_uploader("Upload Profile Image", type=['jpg', 'jpeg', 'png'])

    # Save user data to database upon form submission
    if st.button("Submit"):
        if username and email:
            if uploaded_image is not None:
                # Convert uploaded image to bytes
                image_bytes = uploaded_image.read()
                insert_user_data(username, email, image_bytes)
                st.success("User data saved successfully!")
            else:
                st.error("Please upload a profile image.")
        else:
            st.error("Please fill in all the fields.")

    # Display user data including uploaded images
    st.header("User Data:")
    user_data = get_user_data()
    for user in user_data:
        st.write(f"Username: {user[1]}")
        st.write(f"Email: {user[2]}")
        if user[3] is not None:
            # Display uploaded image
            image = Image.open(io.BytesIO(user[3]))
            st.image(image, caption='Uploaded Image', use_column_width=True)

if __name__ == "__main__":
    main()

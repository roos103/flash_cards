import streamlit as st
import json
import os

# --- Constants & Config ---
# We store data in a subfolder now to keep things tidy and easy to gitignore
DATA_FOLDER = "user_data"
USERS_FILE = os.path.join(DATA_FOLDER, "users.json")

st.set_page_config(page_title="Vibe Cards", page_icon="⚡", layout="centered")

# --- Helper Functions ---
def ensure_data_folder():
    if not os.path.exists(DATA_FOLDER):
        os.makedirs(DATA_FOLDER)

def load_users():
    ensure_data_folder()
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_users(users):
    ensure_data_folder()
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)

def get_user_deck_file(username):
    ensure_data_folder()
    return os.path.join(DATA_FOLDER, f"{username}_deck.json")

def load_deck(username):
    deck_path = get_user_deck_file(username)
    if os.path.exists(deck_path):
        with open(deck_path, "r") as f:
            return json.load(f)
    # Default starter deck for new users
    return [
        {"id": 1, "front": f"Welcome {username}!", "back": "This is your private deck."},
        {"id": 2, "front": "Where is this saved?", "back": f"In user_data/{username}_deck.json"},
    ]

def save_deck(username, deck):
    deck_path = get_user_deck_file(username)
    with open(deck_path, "w") as f:
        json.dump(deck, f)

# --- Session State Initialization ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "current_index" not in st.session_state:
    st.session_state.current_index = 0
if "is_flipped" not in st.session_state:
    st.session_state.is_flipped = False

# --- UI Styling ---
st.markdown("""
<style>
    .stApp {
        background-color: #0e1117;
        color: #fafafa;
    }
    .card-container {
        background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
        border: 1px solid #374151;
        border-radius: 20px;
        padding: 50px;
        text-align: center;
        min-height: 300px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5);
    }
    .card-text {
        font-size: 28px;
        font-weight: bold;
        color: #e5e7eb;
    }
    .label-text {
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 2px;
        color: #6366f1;
        margin-bottom: 10px;
    }
    .stButton button {
        border-radius: 12px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# --- LOGIN / SIGNUP SCREEN ---
if not st.session_state.logged_in:
    st.markdown("## ⚡ **Vibe Cards**")
    
    auth_mode = st.radio("Auth Mode", ["Login", "Sign Up"], horizontal=True, label_visibility="collapsed")
    
    if auth_mode == "Login":
        with st.form("login_form"):
            st.subheader("Login")
            username_input = st.text_input("Username")
            password_input = st.text_input("Password", type="password")
            submit_login = st.form_submit_button("Log In")
            
            if submit_login:
                users = load_users()
                if username_input in users and users[username_input] == password_input:
                    st.session_state.logged_in = True
                    st.session_state.username = username_input
                    # Load that specific user's deck
                    st.session_state.deck = load_deck(username_input)
                    st.success("Logged in!")
                    st.rerun()
                else:
                    st.error("Invalid username or password")

    else: # Sign Up
        with st.form("signup_form"):
            st.subheader("Create Account")
            new_username = st.text_input("Choose Username")
            new_password = st.text_input("Choose Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            submit_signup = st.form_submit_button("Sign Up")
            
            if submit_signup:
                if not new_username or not new_password:
                     st.error("Please fill in all fields.")
                elif new_password != confirm_password:
                    st.error("Passwords do not match.")
                else:
                    users = load_users()
                    if new_username in users:
                        st.error("Username already exists.")
                    else:
                        users[new_username] = new_password
                        save_users(users)
                        st.success("Account created! Please log in.")

# --- MAIN APP (Only shown if logged in) ---
else:
    # App Header
    col1, col2 = st.columns([1, 4])
    with col1:
        st.markdown(f"## ⚡ **{st.session_state.username}**")
    with col2:
        c2_1, c2_2 = st.columns([3, 1])
        with c2_1:
             mode = st.radio("Mode", ["Study", "Editor"], horizontal=True, label_visibility="collapsed")
        with c2_2:
             if st.button("Logout"):
                 st.session_state.logged_in = False
                 st.session_state.username = ""
                 st.rerun()

    st.divider()

    # --- MODE: STUDY ---
    if mode == "Study":
        if not st.session_state.deck:
            st.info("No cards left! Go to Editor to create some.")
        else:
            # Safety check if index out of bounds
            if st.session_state.current_index >= len(st.session_state.deck):
                 st.session_state.current_index = 0
            
            # Get current card (double check deck is not empty after safety check)
            if st.session_state.deck:
                card = st.session_state.deck[st.session_state.current_index]
                
                # Display Card
                content = card["back"] if st.session_state.is_flipped else card["front"]
                label = "ANSWER" if st.session_state.is_flipped else "QUESTION"
                
                st.markdown(f"""
                <div class="card-container">
                    <div class="label-text">{label}</div>
                    <div class="card-text">{content}</div>
                </div>
                """, unsafe_allow_html=True)

                st.write("") # Spacer

                # Controls
                c1, c2, c3 = st.columns([1, 2, 1])
                
                with c1:
                    if st.button("← Prev", use_container_width=True):
                        st.session_state.is_flipped = False
                        st.session_state.current_index = (st.session_state.current_index - 1) % len(st.session_state.deck)
                        st.rerun()

                with c2:
                    flip_label = "Show Question" if st.session_state.is_flipped else "Reveal Answer"
                    type_btn = "secondary" if st.session_state.is_flipped else "primary"
                    if st.button(flip_label, type=type_btn, use_container_width=True):
                        st.session_state.is_flipped = not st.session_state.is_flipped
                        st.rerun()

                with c3:
                    if st.button("Next →", use_container_width=True):
                        st.session_state.is_flipped = False
                        st.session_state.current_index = (st.session_state.current_index + 1) % len(st.session_state.deck)
                        st.rerun()

                # Progress Bar
                progress = (st.session_state.current_index + 1) / len(st.session_state.deck)
                st.progress(progress)
                st.caption(f"Card {st.session_state.current_index + 1} of {len(st.session_state.deck)}")

    # --- MODE: EDITOR ---
    else:
        st.subheader("Add New Card")
        
        with st.form("add_card_form", clear_on_submit=True):
            new_front = st.text_input("Front (Question)")
            new_back = st.text_area("Back (Answer)")
            submitted = st.form_submit_button("Add Card")
            
            if submitted and new_front and new_back:
                st.session_state.deck.append({
                    "id": len(st.session_state.deck) + 100, 
                    "front": new_front,
                    "back": new_back
                })
                # Pass username to save_deck so it goes to the right file
                save_deck(st.session_state.username, st.session_state.deck)
                st.success("Card added!")
                st.rerun()

        st.subheader("Your Deck")
        for i, card in enumerate(st.session_state.deck):
            with st.expander(f"{i+1}. {card['front']}"):
                st.write(f"**Answer:** {card['back']}")
                if st.button("Delete", key=f"del_{card['id']}"):
                    st.session_state.deck.pop(i)
                    save_deck(st.session_state.username, st.session_state.deck)
                    # Adjust index if needed
                    if st.session_state.current_index >= len(st.session_state.deck):
                        st.session_state.current_index = max(0, len(st.session_state.deck) - 1)
                    st.rerun()

        if st.button("Export Deck to JSON"):
            json_str = json.dumps(st.session_state.deck, indent=2)
            st.download_button(
                label="Download JSON",
                data=json_str,
                file_name=f"{st.session_state.username}_deck.json",
                mime="application/json"
            )
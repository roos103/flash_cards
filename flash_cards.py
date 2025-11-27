import streamlit as st
import json
import os
import random
import difflib
import csv
import io

# --- Constants & Config ---
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
        {
            "id": 1, 
            "front": f"Welcome {username}!", 
            "back": "This is your private deck.", 
            "enable_write": False, 
            "enable_choice": False, 
            "distractors": []
        },
        {
            "id": 2, 
            "front": "Type the answer: What is the capital of France?", 
            "back": "Paris",
            "enable_write": True,
            "enable_choice": True,
            "distractors": ["London", "Berlin", "Madrid"]
        },
    ]

def save_deck(username, deck):
    deck_path = get_user_deck_file(username)
    with open(deck_path, "w") as f:
        json.dump(deck, f)

def check_similarity(user_input, correct_answer):
    # Returns a ratio from 0.0 to 1.0
    return difflib.SequenceMatcher(None, user_input.lower().strip(), correct_answer.lower().strip()).ratio()

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
    /* Style tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #1f2937;
        border-radius: 4px;
        color: #fff;
    }
    .stTabs [aria-selected="true"] {
        background-color: #4f46e5;
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
            if st.session_state.current_index >= len(st.session_state.deck):
                 st.session_state.current_index = 0
            
            if st.session_state.deck:
                card = st.session_state.deck[st.session_state.current_index]
                
                # Determine available modes for this card
                available_tabs = ["Flip"]
                if card.get("enable_write", False):
                    available_tabs.append("Type")
                if card.get("enable_choice", False) and card.get("distractors"):
                    available_tabs.append("Quiz")

                # Create Tabs
                tabs = st.tabs(available_tabs)

                # --- TAB 1: FLIP (Classic) ---
                with tabs[0]:
                    content = card["back"] if st.session_state.is_flipped else card["front"]
                    label = "ANSWER" if st.session_state.is_flipped else "QUESTION"
                    
                    st.markdown(f"""
                    <div class="card-container">
                        <div class="label-text">{label}</div>
                        <div class="card-text">{content}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Flip Button
                    flip_label = "Show Question" if st.session_state.is_flipped else "Reveal Answer"
                    if st.button(flip_label, use_container_width=True):
                        st.session_state.is_flipped = not st.session_state.is_flipped
                        st.rerun()

                # --- TAB 2: TYPE ANSWER ---
                if "Type" in available_tabs:
                    # Find index of "Type" to use correct tab
                    with tabs[available_tabs.index("Type")]:
                        st.subheader("Type your answer:")
                        st.info(card["front"])
                        
                        user_type_input = st.text_input("Your Answer", key=f"type_{card['id']}")
                        
                        if user_type_input:
                            similarity = check_similarity(user_type_input, card["back"])
                            if similarity == 1.0:
                                st.success(f"Correct! The answer is indeed: {card['back']}")
                                st.balloons()
                            elif similarity > 0.7:
                                st.warning(f"Close! You wrote '{user_type_input}', but the answer is '{card['back']}'.")
                            else:
                                st.error(f"Incorrect. The right answer is: {card['back']}")

                # --- TAB 3: QUIZ (Multiple Choice) ---
                if "Quiz" in available_tabs:
                    with tabs[available_tabs.index("Quiz")]:
                        st.subheader("Choose the correct answer:")
                        st.info(card["front"])
                        
                        # Generate options deterministicly based on card ID so they don't reshuffle on click
                        # We combine distractors + real answer
                        options = card.get("distractors", []) + [card["back"]]
                        # Use card ID as seed for shuffle so it stays consistent for this card
                        random.Random(card['id']).shuffle(options)
                        
                        choice = st.radio("Options:", options, key=f"quiz_{card['id']}")
                        
                        if st.button("Check Answer", key=f"check_{card['id']}"):
                            if choice == card["back"]:
                                st.success("Correct!")
                                st.balloons()
                            else:
                                st.error(f"Wrong! The correct answer was: {card['back']}")

                st.divider()

                # Navigation
                c1, c2, c3 = st.columns([1, 2, 1])
                with c1:
                    if st.button("← Prev", use_container_width=True):
                        st.session_state.is_flipped = False
                        st.session_state.current_index = (st.session_state.current_index - 1) % len(st.session_state.deck)
                        st.rerun()
                with c3:
                    if st.button("Next →", use_container_width=True):
                        st.session_state.is_flipped = False
                        st.session_state.current_index = (st.session_state.current_index + 1) % len(st.session_state.deck)
                        st.rerun()

                progress = (st.session_state.current_index + 1) / len(st.session_state.deck)
                st.progress(progress)

    # --- MODE: EDITOR ---
    else:
        # BULK IMPORT SECTION
        with st.expander("Bulk Import via CSV", expanded=True):
            st.markdown("""
            **Format:** `Question, Type Code, Answer, Distractor 1, Distractor 2, ...`
            
            **Type Codes:**
            * `1`: Write-in Only
            * `2`: Multiple Choice Only
            * `3`: Both
            """)
            
            csv_input = st.text_area("Paste CSV Data Here", height=150)
            
            if st.button("Process Bulk Import"):
                if csv_input:
                    try:
                        # Use csv module to handle quoted strings properly
                        f = io.StringIO(csv_input)
                        reader = csv.reader(f, skipinitialspace=True)
                        
                        added_count = 0
                        for row in reader:
                            if len(row) < 3:
                                continue # Skip invalid rows
                                
                            front = row[0].strip()
                            type_code = row[1].strip()
                            back = row[2].strip()
                            distractors = [d.strip() for d in row[3:] if d.strip()]
                            
                            # Logic for types
                            enable_write = False
                            enable_choice = False
                            
                            if type_code == '1':
                                enable_write = True
                            elif type_code == '2':
                                enable_choice = True
                            elif type_code == '3':
                                enable_write = True
                                enable_choice = True
                            
                            # Validation: Disable choice if no distractors
                            if enable_choice and not distractors:
                                st.warning(f"Skipping choice mode for '{front}' - no distractors found.")
                                enable_choice = False

                            st.session_state.deck.append({
                                "id": len(st.session_state.deck) + 1000 + random.randint(0, 9999),
                                "front": front,
                                "back": back,
                                "enable_write": enable_write,
                                "enable_choice": enable_choice,
                                "distractors": distractors
                            })
                            added_count += 1
                        
                        save_deck(st.session_state.username, st.session_state.deck)
                        st.success(f"Successfully added {added_count} cards!")
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Error parsing CSV: {e}")

        st.divider()
        st.subheader("Add Single Card")
        
        with st.form("add_card_form", clear_on_submit=True):
            new_front = st.text_input("Front (Question)")
            new_back = st.text_input("Back (Answer)")
            
            st.markdown("#### Interaction Options")
            col_opts_1, col_opts_2 = st.columns(2)
            with col_opts_1:
                enable_write = st.checkbox("Enable Typing Answer")
            with col_opts_2:
                enable_choice = st.checkbox("Enable Multiple Choice")
                
            distractors_input = st.text_area("Wrong Answers (one per line) - Only for Multiple Choice")
            
            submitted = st.form_submit_button("Add Card")
            
            if submitted and new_front and new_back:
                distractors_list = [line.strip() for line in distractors_input.split('\n') if line.strip()]
                
                if enable_choice and not distractors_list:
                    st.error("You enabled Multiple Choice but didn't provide any wrong answers!")
                else:
                    st.session_state.deck.append({
                        "id": len(st.session_state.deck) + 100, 
                        "front": new_front,
                        "back": new_back,
                        "enable_write": enable_write,
                        "enable_choice": enable_choice,
                        "distractors": distractors_list
                    })
                    save_deck(st.session_state.username, st.session_state.deck)
                    st.success("Card added!")
                    st.rerun()

        st.subheader("Your Deck")
        for i, card in enumerate(st.session_state.deck):
            with st.expander(f"{i+1}. {card['front']}"):
                st.write(f"**Answer:** {card['back']}")
                modes = ["Flip"]
                if card.get("enable_write"): modes.append("Type")
                if card.get("enable_choice"): modes.append("Quiz")
                st.caption(f"Modes: {', '.join(modes)}")
                
                if card.get("distractors"):
                     st.write(f"**Wrong Options:** {', '.join(card['distractors'])}")
                     
                if st.button("Delete", key=f"del_{card['id']}"):
                    st.session_state.deck.pop(i)
                    save_deck(st.session_state.username, st.session_state.deck)
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
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

st.set_page_config(page_title="Vibe Cards", page_icon="⚡", layout="wide")

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
            data = json.load(f)
            if isinstance(data, list):
                deck_dict = {"Default": data}
            else:
                deck_dict = data
            
            # Ensure stats exist
            for lst in deck_dict.values():
                for card in lst:
                    if "stats" not in card:
                        card["stats"] = {"attempts": 0, "history": []}
            return deck_dict
            
    return {
        "Default": [
            {
                "id": 1, 
                "front": f"Welcome {username}!", 
                "back": "This is your private deck.", 
                "enable_write": False, 
                "enable_choice": False, 
                "distractors": [],
                "stats": {"attempts": 0, "history": []}
            }
        ]
    }

def save_deck(username, deck_data):
    deck_path = get_user_deck_file(username)
    with open(deck_path, "w") as f:
        json.dump(deck_data, f)

def check_similarity(user_input, correct_answer):
    return difflib.SequenceMatcher(None, user_input.lower().strip(), correct_answer.lower().strip()).ratio()

def update_card_stats(card, is_correct):
    if "stats" not in card:
        card["stats"] = {"attempts": 0, "history": []}
    card["stats"]["attempts"] += 1
    card["stats"]["history"].append(is_correct)
    if len(card["stats"]["history"]) > 20:
        card["stats"]["history"].pop(0)
    save_deck(st.session_state.username, st.session_state.deck_data)

def update_session_score(result_type):
    # result_type: "correct", "partial", "missed"
    if "session_score" not in st.session_state:
        st.session_state.session_score = {"correct": 0, "partial": 0, "missed": 0}
    st.session_state.session_score[result_type] += 1

# --- Session State Init ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
# Navigation States
if "nav_phase" not in st.session_state:
    st.session_state.nav_phase = "dashboard" # dashboard, config, session
if "selected_list_name" not in st.session_state:
    st.session_state.selected_list_name = None
if "session_settings" not in st.session_state:
    st.session_state.session_settings = {"order": "Sequential", "mode": "Flip Only"}
if "session_score" not in st.session_state:
    st.session_state.session_score = {"correct": 0, "partial": 0, "missed": 0}

# Study State
if "current_index" not in st.session_state:
    st.session_state.current_index = 0
if "is_flipped" not in st.session_state:
    st.session_state.is_flipped = False
if "study_indices" not in st.session_state:
    st.session_state.study_indices = []

# Editor State
if "selected_card_ids" not in st.session_state:
    st.session_state.selected_card_ids = set()

# --- Custom CSS ---
st.markdown("""
<style>
    /* Global App Style */
    .stApp {
        background-color: #0e1117;
        color: #fafafa;
    }
    
    /* The Flashcard Container */
    .vibe-card {
        background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
        border: 1px solid #374151;
        border-radius: 20px;
        padding: 40px;
        text-align: center;
        min-height: 400px; /* Fixed height to prevent collapse */
        display: flex;
        flex-direction: column;
        justify-content: space-between; /* Space out content */
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.6);
        margin-bottom: 20px;
    }
    
    /* Card Content Text */
    .card-content-area {
        flex-grow: 1;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        min-height: 150px;
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
        color: #818cf8;
        margin-bottom: 15px;
    }
    
    /* Dashboard List Card */
    .list-card {
        background-color: #1f2937;
        border: 1px solid #374151;
        border-radius: 12px;
        padding: 20px;
        cursor: pointer;
        transition: transform 0.2s;
        text-align: center;
    }
    .list-card:hover {
        border-color: #6366f1;
        transform: translateY(-2px);
    }
    
    /* Stats Bar */
    .score-box {
        background-color: #111827;
        padding: 10px 20px;
        border-radius: 10px;
        border: 1px solid #374151;
        text-align: center;
        font-weight: bold;
    }
    
    /* Customizing Inputs inside Card */
    .stTextInput input {
        text-align: center;
        background-color: #111827;
        border: 1px solid #4b5563;
        color: white;
    }
    
    /* Make buttons pop */
    .stButton button {
        border-radius: 10px;
        font-weight: 600;
        border: none;
        transition: all 0.3s ease;
    }
</style>
""", unsafe_allow_html=True)

# --- LOGIN FLOW ---
if not st.session_state.logged_in:
    st.markdown("## ⚡ **Vibe Cards**")
    col1, col2 = st.columns([1,1])
    with col1:
        auth_mode = st.radio("Auth Mode", ["Login", "Sign Up"], horizontal=True, label_visibility="collapsed")
    
    if auth_mode == "Login":
        with st.form("login_form"):
            username_input = st.text_input("Username")
            password_input = st.text_input("Password", type="password")
            if st.form_submit_button("Log In"):
                users = load_users()
                if username_input in users and users[username_input] == password_input:
                    st.session_state.logged_in = True
                    st.session_state.username = username_input
                    st.session_state.deck_data = load_deck(username_input)
                    st.rerun()
                else:
                    st.error("Invalid credentials")
    else:
        with st.form("signup_form"):
            new_username = st.text_input("Choose Username")
            new_password = st.text_input("Choose Password", type="password")
            if st.form_submit_button("Sign Up"):
                users = load_users()
                if new_username in users:
                    st.error("Taken!")
                else:
                    users[new_username] = new_password
                    save_users(users)
                    st.success("Created! Log in.")

# --- APP FLOW ---
else:
    # Sidebar Global Controls
    with st.sidebar:
        st.title(f"👤 {st.session_state.username}")
        app_mode = st.radio("App Section", ["Study Room", "Deck Editor"], index=0)
        st.divider()
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()

    # =========================================================
    # SECTION: STUDY ROOM (THE FUNNEL)
    # =========================================================
    if app_mode == "Study Room":
        
        # --- PHASE 1: DASHBOARD (List Selection) ---
        if st.session_state.nav_phase == "dashboard":
            st.title("📚 Library")
            
            # Search / Filter
            search_query = st.text_input("Search Lists...", placeholder="Type to filter...").lower()
            
            st.markdown("### Available Decks")
            
            # Filter logic
            all_lists = list(st.session_state.deck_data.keys())
            filtered_lists = [l for l in all_lists if search_query in l.lower()]
            
            if not filtered_lists:
                st.info("No decks found matching your search.")
            else:
                # Grid Layout for Lists
                cols = st.columns(3)
                for i, list_name in enumerate(filtered_lists):
                    deck = st.session_state.deck_data[list_name]
                    with cols[i % 3]:
                        # Render a "Card" for the list
                        with st.container(border=True):
                            st.subheader(list_name)
                            st.caption(f"{len(deck)} Cards")
                            if st.button(f"Open {list_name}", key=f"btn_{list_name}", use_container_width=True):
                                st.session_state.selected_list_name = list_name
                                st.session_state.nav_phase = "config"
                                st.rerun()

        # --- PHASE 2: CONFIGURATION ---
        elif st.session_state.nav_phase == "config":
            st.button("← Back to Library", on_click=lambda: st.session_state.update(nav_phase="dashboard"))
            
            st.title(f"⚙️ Setup: {st.session_state.selected_list_name}")
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### 1. How should we order the cards?")
                order = st.radio("Order", ["Sequential", "Random"], key="cfg_order")
            
            with col2:
                st.markdown("#### 2. How do you want to study?")
                mode = st.radio("Mode", ["Flip Only (Review)", "Test Myself (Interactive)"], key="cfg_mode")
            
            st.divider()
            
            if st.button("🚀 Start Session", type="primary", use_container_width=True):
                # Init Session
                st.session_state.session_settings = {"order": order, "mode": mode}
                st.session_state.session_score = {"correct": 0, "partial": 0, "missed": 0}
                st.session_state.current_index = 0
                st.session_state.is_flipped = False
                
                # Prep Indices
                deck = st.session_state.deck_data[st.session_state.selected_list_name]
                indices = list(range(len(deck)))
                if order == "Random":
                    random.shuffle(indices)
                st.session_state.study_indices = indices
                
                st.session_state.nav_phase = "session"
                st.rerun()

        # --- PHASE 3: SESSION ---
        elif st.session_state.nav_phase == "session":
            deck_name = st.session_state.selected_list_name
            deck = st.session_state.deck_data[deck_name]
            indices = st.session_state.study_indices
            settings = st.session_state.session_settings
            
            # Header with Scoreboard (if testing)
            col_head, col_score = st.columns([1, 2])
            with col_head:
                st.button("← Exit", on_click=lambda: st.session_state.update(nav_phase="dashboard"))
            
            if settings["mode"] == "Test Myself (Interactive)":
                with col_score:
                    s = st.session_state.session_score
                    c1, c2, c3 = st.columns(3)
                    c1.markdown(f"<div class='score-box' style='color:#4ade80'>Correct: {s['correct']}</div>", unsafe_allow_html=True)
                    c2.markdown(f"<div class='score-box' style='color:#facc15'>Close: {s['partial']}</div>", unsafe_allow_html=True)
                    c3.markdown(f"<div class='score-box' style='color:#f87171'>Missed: {s['missed']}</div>", unsafe_allow_html=True)

            # Progress
            if len(indices) == 0:
                st.warning("Empty Deck.")
                st.stop()
                
            if st.session_state.current_index >= len(indices):
                st.session_state.current_index = 0 # Loop or finish? Loop for now.
            
            real_index = indices[st.session_state.current_index]
            card = deck[real_index]
            
            # --- THE CARD UI ---
            st.write("") # Spacer
            
            # Determine Interaction Type
            # If "Test Myself", we look at card capabilities. Priority: Choice > Write > Flip
            interaction_type = "Flip"
            if settings["mode"] == "Test Myself (Interactive)":
                if card.get("enable_choice") and card.get("distractors"):
                    interaction_type = "Choice"
                elif card.get("enable_write"):
                    interaction_type = "Write"
            
            # OPEN CSS CONTAINER FOR CARD
            st.markdown('<div class="vibe-card">', unsafe_allow_html=True)
            
            # 1. Label
            label = "QUESTION"
            if st.session_state.is_flipped:
                label = "ANSWER"
            st.markdown(f'<div class="label-text">{label}</div>', unsafe_allow_html=True)
            
            # 2. Content Area
            content = card["front"]
            if st.session_state.is_flipped:
                content = card["back"]
            
            st.markdown(f'<div class="card-content-area"><div class="card-text">{content}</div></div>', unsafe_allow_html=True)
            
            # 3. Interactive Area (Inside the Card)
            # We use st.container to group widgets visually inside our CSS div
            
            if not st.session_state.is_flipped:
                
                if interaction_type == "Write":
                    st.write("Type your answer:")
                    user_input = st.text_input("Answer", key=f"write_{card['id']}", label_visibility="collapsed")
                    if user_input:
                        # Auto-grade
                        sim = check_similarity(user_input, card["back"])
                        st.session_state.is_flipped = True
                        if sim == 1.0:
                            st.success("Perfect!")
                            update_card_stats(card, True)
                            update_session_score("correct")
                        elif sim > 0.7:
                            st.warning(f"Close! It was: {card['back']}")
                            update_card_stats(card, False)
                            update_session_score("partial")
                        else:
                            st.error(f"Incorrect. It was: {card['back']}")
                            update_card_stats(card, False)
                            update_session_score("missed")
                        st.button("Next Card ->") # Just to trigger rerun to show flipped state
                
                elif interaction_type == "Choice":
                    st.write("Select the correct answer:")
                    opts = card.get("distractors", []) + [card["back"]]
                    random.Random(card['id']).shuffle(opts)
                    
                    # We use columns to make buttons look like choices
                    for opt in opts:
                        if st.button(opt, key=f"opt_{card['id']}_{opt}", use_container_width=True):
                            st.session_state.is_flipped = True
                            if opt == card["back"]:
                                st.success("Correct!")
                                update_card_stats(card, True)
                                update_session_score("correct")
                            else:
                                st.error(f"Wrong! It was {card['back']}")
                                update_card_stats(card, False)
                                update_session_score("missed")
                            st.rerun()

                else: # Flip Mode
                    st.write("") # Spacer
                    if st.button("Reveal Answer", use_container_width=True):
                        st.session_state.is_flipped = True
                        st.rerun()
            
            else:
                # Flipped State controls
                st.write("---")
                if settings["mode"] == "Flip Only (Review)":
                    # Self Grading
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("Got it right", use_container_width=True):
                            update_card_stats(card, True)
                            st.session_state.is_flipped = False
                            st.session_state.current_index = (st.session_state.current_index + 1) % len(indices)
                            st.rerun()
                    with c2:
                        if st.button("Missed it", use_container_width=True):
                            update_card_stats(card, False)
                            st.session_state.is_flipped = False
                            st.session_state.current_index = (st.session_state.current_index + 1) % len(indices)
                            st.rerun()
                else:
                    # Interactive Mode just needs a Next button since grading happened on submit
                    if st.button("Next Card ➡️", use_container_width=True):
                        st.session_state.is_flipped = False
                        st.session_state.current_index = (st.session_state.current_index + 1) % len(indices)
                        st.rerun()

            # CLOSE CSS CONTAINER
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Footer Nav
            progress = (st.session_state.current_index + 1) / len(indices)
            st.progress(progress)
            st.caption(f"Card {st.session_state.current_index + 1} of {len(indices)}")

    # =========================================================
    # SECTION: EDITOR (Admin)
    # =========================================================
    elif app_mode == "Deck Editor":
        st.title("✏️ Deck Editor")
        
        # Select Deck to Edit
        deck_names = list(st.session_state.deck_data.keys())
        active_deck = st.selectbox("Select Deck", deck_names)
        
        # New Deck / Delete Deck controls
        c_new1, c_new2 = st.columns(2)
        with c_new1:
            new_deck_name = st.text_input("Create New Deck Name")
            if st.button("Create Deck") and new_deck_name:
                if new_deck_name not in st.session_state.deck_data:
                    st.session_state.deck_data[new_deck_name] = []
                    save_deck(st.session_state.username, st.session_state.deck_data)
                    st.success("Created!")
                    st.rerun()
        with c_new2:
            if st.button("Delete Current Deck") and len(deck_names) > 1:
                del st.session_state.deck_data[active_deck]
                save_deck(st.session_state.username, st.session_state.deck_data)
                st.rerun()
                
        st.divider()
        
        # Add Card Form
        st.subheader(f"Add Card to '{active_deck}'")
        with st.form("add_card"):
            front = st.text_input("Front (Question)")
            back = st.text_input("Back (Answer)")
            
            c1, c2 = st.columns(2)
            with c1: en_write = st.checkbox("Enable Typing")
            with c2: en_choice = st.checkbox("Enable Choice")
            
            distractors = st.text_area("Distractors (one per line, for Choice)")
            
            if st.form_submit_button("Add Card"):
                d_list = [x.strip() for x in distractors.split('\n') if x.strip()]
                st.session_state.deck_data[active_deck].append({
                    "id": random.randint(100000, 999999),
                    "front": front,
                    "back": back,
                    "enable_write": en_write,
                    "enable_choice": en_choice,
                    "distractors": d_list,
                    "stats": {"attempts": 0, "history": []}
                })
                save_deck(st.session_state.username, st.session_state.deck_data)
                st.success("Added!")
        
        st.divider()
        
        # List Cards
        st.subheader("Manage Cards")
        current_deck = st.session_state.deck_data[active_deck]
        for i, card in enumerate(current_deck):
            with st.expander(f"{card['front']} -> {card['back']}"):
                if st.button("Delete", key=f"del_{card['id']}"):
                    st.session_state.deck_data[active_deck].pop(i)
                    save_deck(st.session_state.username, st.session_state.deck_data)
                    st.rerun()
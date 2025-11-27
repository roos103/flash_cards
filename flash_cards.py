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
            # Migration: If old format (list), convert to dict
            if isinstance(data, list):
                return {"Default": data}
            return data
            
    # Default starter deck for new users
    return {
        "Default": [
            {
                "id": 1, 
                "front": f"Welcome {username}!", 
                "back": "This is your private deck.", 
                "enable_write": False, 
                "enable_choice": False, 
                "distractors": []
            }
        ]
    }

def save_deck(username, deck_data):
    deck_path = get_user_deck_file(username)
    with open(deck_path, "w") as f:
        json.dump(deck_data, f)

def check_similarity(user_input, correct_answer):
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
if "active_list" not in st.session_state:
    st.session_state.active_list = "Default"
if "selected_card_ids" not in st.session_state:
    st.session_state.selected_card_ids = set()

# New State for Study Order
if "study_order" not in st.session_state:
    st.session_state.study_order = "Sequential" # or "Random"
if "study_indices" not in st.session_state:
    st.session_state.study_indices = []
if "last_active_list" not in st.session_state:
    st.session_state.last_active_list = ""
if "last_deck_len" not in st.session_state:
    st.session_state.last_deck_len = 0

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
    
    col1, col2 = st.columns([1,1])
    with col1:
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
                    st.session_state.deck_data = load_deck(username_input)
                    if "Default" in st.session_state.deck_data:
                        st.session_state.active_list = "Default"
                    else:
                        st.session_state.active_list = list(st.session_state.deck_data.keys())[0]
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

# --- MAIN APP ---
else:
    # --- SIDEBAR: LIST MANAGEMENT ---
    with st.sidebar:
        st.header(f"User: {st.session_state.username}")
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()
            
        st.divider()
        st.subheader("🗂️ My Lists")
        
        # Ensure active list is valid
        if st.session_state.active_list not in st.session_state.deck_data:
            if st.session_state.deck_data:
                st.session_state.active_list = list(st.session_state.deck_data.keys())[0]
            else:
                st.session_state.deck_data["Default"] = []
                st.session_state.active_list = "Default"

        # List Selector
        list_names = list(st.session_state.deck_data.keys())
        selected_list = st.selectbox("Select List", list_names, index=list_names.index(st.session_state.active_list))
        
        if selected_list != st.session_state.active_list:
            st.session_state.active_list = selected_list
            st.session_state.current_index = 0
            st.session_state.is_flipped = False
            st.rerun()
            
        st.divider()
        
        # Create New List
        with st.popover("Create New List"):
            new_list_name = st.text_input("New List Name")
            if st.button("Create"):
                if new_list_name and new_list_name not in st.session_state.deck_data:
                    st.session_state.deck_data[new_list_name] = []
                    save_deck(st.session_state.username, st.session_state.deck_data)
                    st.session_state.active_list = new_list_name
                    st.success(f"Created {new_list_name}")
                    st.rerun()
                elif new_list_name in st.session_state.deck_data:
                    st.error("List already exists")

        if len(list_names) > 1:
            if st.button(f"Delete '{st.session_state.active_list}'"):
                del st.session_state.deck_data[st.session_state.active_list]
                st.session_state.active_list = list(st.session_state.deck_data.keys())[0]
                save_deck(st.session_state.username, st.session_state.deck_data)
                st.rerun()

    # --- MAIN CONTENT ---
    current_deck = st.session_state.deck_data[st.session_state.active_list]

    # App Header
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.markdown(f"## ⚡ **{st.session_state.active_list}** ({len(current_deck)} cards)")
    with col_h2:
         mode = st.radio("Mode", ["Study", "Editor"], horizontal=True, label_visibility="collapsed")

    st.divider()

    # --- MODE: STUDY ---
    if mode == "Study":
        if not current_deck:
            st.info("No cards in this list! Go to Editor to create some.")
        else:
            # --- STUDY ORDER LOGIC ---
            # Order Selector
            c_ord1, c_ord2 = st.columns([1, 4])
            with c_ord1:
                st.caption("List Order")
                new_order = st.selectbox("Order", ["Sequential", "Random"], label_visibility="collapsed", key="order_selector")

            # Detect changes (List changed OR Mode changed OR Deck length changed)
            needs_reshuffle = False
            if new_order != st.session_state.study_order:
                st.session_state.study_order = new_order
                needs_reshuffle = True
            
            if st.session_state.active_list != st.session_state.last_active_list:
                st.session_state.last_active_list = st.session_state.active_list
                needs_reshuffle = True
            
            if len(current_deck) != st.session_state.last_deck_len:
                st.session_state.last_deck_len = len(current_deck)
                needs_reshuffle = True

            # If tracking array is empty/mismatched size, we also need to shuffle
            if len(st.session_state.study_indices) != len(current_deck):
                needs_reshuffle = True

            # Perform the shuffle/reset if needed
            if needs_reshuffle:
                st.session_state.current_index = 0
                st.session_state.is_flipped = False
                if st.session_state.study_order == "Random":
                    indices = list(range(len(current_deck)))
                    random.shuffle(indices)
                    st.session_state.study_indices = indices
                else:
                    st.session_state.study_indices = list(range(len(current_deck)))
            
            # --- DISPLAY CARD ---
            # Safety check: ensure current_index is valid
            if st.session_state.current_index >= len(st.session_state.study_indices):
                 st.session_state.current_index = 0
            
            # Map visual index -> Real card index
            real_index = st.session_state.study_indices[st.session_state.current_index]
            card = current_deck[real_index]
            
            # Determine available modes
            available_tabs = ["Flip"]
            if card.get("enable_write", False):
                available_tabs.append("Type")
            if card.get("enable_choice", False) and card.get("distractors"):
                available_tabs.append("Quiz")

            tabs = st.tabs(available_tabs)

            # TAB 1: FLIP
            with tabs[0]:
                content = card["back"] if st.session_state.is_flipped else card["front"]
                label = "ANSWER" if st.session_state.is_flipped else "QUESTION"
                
                st.markdown(f"""
                <div class="card-container">
                    <div class="label-text">{label}</div>
                    <div class="card-text">{content}</div>
                </div>
                """, unsafe_allow_html=True)
                
                flip_label = "Show Question" if st.session_state.is_flipped else "Reveal Answer"
                if st.button(flip_label, use_container_width=True):
                    st.session_state.is_flipped = not st.session_state.is_flipped
                    st.rerun()

            # TAB 2: TYPE
            if "Type" in available_tabs:
                with tabs[available_tabs.index("Type")]:
                    st.subheader("Type your answer:")
                    st.info(card["front"])
                    user_type_input = st.text_input("Your Answer", key=f"type_{card['id']}")
                    if user_type_input:
                        similarity = check_similarity(user_type_input, card["back"])
                        if similarity == 1.0:
                            st.success(f"Correct! {card['back']}")
                            st.balloons()
                        elif similarity > 0.7:
                            st.warning(f"Close! Answer: '{card['back']}'.")
                        else:
                            st.error(f"Incorrect. Answer: {card['back']}")

            # TAB 3: QUIZ
            if "Quiz" in available_tabs:
                with tabs[available_tabs.index("Quiz")]:
                    st.subheader("Choose the correct answer:")
                    st.info(card["front"])
                    options = card.get("distractors", []) + [card["back"]]
                    random.Random(card['id']).shuffle(options)
                    choice = st.radio("Options:", options, key=f"quiz_{card['id']}")
                    if st.button("Check Answer", key=f"check_{card['id']}"):
                        if choice == card["back"]:
                            st.success("Correct!")
                            st.balloons()
                        else:
                            st.error(f"Wrong! Answer: {card['back']}")

            st.divider()

            # Navigation
            c1, c3 = st.columns([1, 1])
            with c1:
                if st.button("← Prev", use_container_width=True):
                    st.session_state.is_flipped = False
                    st.session_state.current_index = (st.session_state.current_index - 1) % len(current_deck)
                    st.rerun()
            with c3:
                if st.button("Next →", use_container_width=True):
                    st.session_state.is_flipped = False
                    st.session_state.current_index = (st.session_state.current_index + 1) % len(current_deck)
                    st.rerun()

            progress = (st.session_state.current_index + 1) / len(current_deck)
            st.progress(progress)
            st.caption(f"Card {st.session_state.current_index + 1} of {len(current_deck)} ({st.session_state.study_order} Order)")

    # --- MODE: EDITOR ---
    else:
        if current_deck:
            with st.expander("🛠️ Bulk Actions (Select Multiple)", expanded=True):
                st.write("Select cards to modify:")
                sel_col1, sel_col2, sel_col3 = st.columns([1, 1, 2])
                with sel_col1:
                    if st.button("Select All"):
                        st.session_state.selected_card_ids = {c['id'] for c in current_deck}
                with sel_col2:
                    if st.button("Deselect All"):
                        st.session_state.selected_card_ids = set()
                
                for card in current_deck:
                    is_checked = card['id'] in st.session_state.selected_card_ids
                    if st.checkbox(f"{card['front']} ({card['back']})", value=is_checked, key=f"sel_{card['id']}"):
                        st.session_state.selected_card_ids.add(card['id'])
                    else:
                        st.session_state.selected_card_ids.discard(card['id'])

                st.markdown("#### Apply Action")
                if not st.session_state.selected_card_ids:
                    st.caption("No cards selected")
                else:
                    action_col1, action_col2 = st.columns(2)
                    with action_col1:
                        target_list = st.selectbox("Target List", [l for l in st.session_state.deck_data.keys() if l != st.session_state.active_list])
                    with action_col2:
                        action_type = st.selectbox("Action", ["Move Selected", "Copy Selected", "Delete Selected"])

                    if st.button(f"Execute: {action_type}"):
                        selected_cards = [c for c in current_deck if c['id'] in st.session_state.selected_card_ids]
                        
                        if action_type == "Delete Selected":
                            new_deck = [c for c in current_deck if c['id'] not in st.session_state.selected_card_ids]
                            st.session_state.deck_data[st.session_state.active_list] = new_deck
                            st.session_state.selected_card_ids = set() 
                            save_deck(st.session_state.username, st.session_state.deck_data)
                            st.success("Deleted selected cards.")
                            st.rerun()
                        elif target_list:
                            cards_to_transfer = []
                            for c in selected_cards:
                                new_card = c.copy()
                                new_card['id'] = new_card['id'] + 10000 + random.randint(0,9999)
                                cards_to_transfer.append(new_card)

                            if action_type == "Copy Selected":
                                st.session_state.deck_data[target_list].extend(cards_to_transfer)
                                save_deck(st.session_state.username, st.session_state.deck_data)
                                st.success(f"Copied {len(cards_to_transfer)} cards to {target_list}.")
                            elif action_type == "Move Selected":
                                st.session_state.deck_data[target_list].extend(cards_to_transfer)
                                new_deck = [c for c in current_deck if c['id'] not in st.session_state.selected_card_ids]
                                st.session_state.deck_data[st.session_state.active_list] = new_deck
                                st.session_state.selected_card_ids = set()
                                save_deck(st.session_state.username, st.session_state.deck_data)
                                st.success(f"Moved {len(cards_to_transfer)} cards to {target_list}.")
                                st.rerun()

        st.divider()

        with st.expander("Import via CSV"):
            st.markdown(f"Adding to list: **{st.session_state.active_list}**")
            st.markdown("""
            **Format:** `Question, Type Code, Answer, Distractor 1, Distractor 2, ...`
            Codes: `1`=Write, `2`=Choice, `3`=Both
            """)
            
            csv_input = st.text_area("Paste CSV Data Here", height=150)
            
            if st.button("Process Bulk Import"):
                if csv_input:
                    try:
                        f = io.StringIO(csv_input)
                        reader = csv.reader(f, skipinitialspace=True)
                        added_count = 0
                        for row in reader:
                            if len(row) < 3: continue 
                            front, type_code, back = row[0].strip(), row[1].strip(), row[2].strip()
                            distractors = [d.strip() for d in row[3:] if d.strip()]
                            enable_write = type_code in ['1', '3']
                            enable_choice = type_code in ['2', '3']
                            if enable_choice and not distractors: enable_choice = False

                            st.session_state.deck_data[st.session_state.active_list].append({
                                "id": random.randint(100000, 999999),
                                "front": front,
                                "back": back,
                                "enable_write": enable_write,
                                "enable_choice": enable_choice,
                                "distractors": distractors
                            })
                            added_count += 1
                        
                        save_deck(st.session_state.username, st.session_state.deck_data)
                        st.success(f"Added {added_count} cards to {st.session_state.active_list}!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error parsing CSV: {e}")

        st.divider()
        st.subheader("Add Single Card")
        with st.form("add_card_form", clear_on_submit=True):
            new_front = st.text_input("Front (Question)")
            new_back = st.text_input("Back (Answer)")
            
            col_opts_1, col_opts_2 = st.columns(2)
            with col_opts_1: enable_write = st.checkbox("Enable Typing")
            with col_opts_2: enable_choice = st.checkbox("Enable Choice")
            
            distractors_input = st.text_area("Wrong Answers (one per line)")
            submitted = st.form_submit_button(f"Add to {st.session_state.active_list}")
            
            if submitted and new_front and new_back:
                distractors_list = [line.strip() for line in distractors_input.split('\n') if line.strip()]
                if enable_choice and not distractors_list:
                    st.error("Missing wrong answers for multiple choice!")
                else:
                    st.session_state.deck_data[st.session_state.active_list].append({
                        "id": random.randint(100000, 999999), 
                        "front": new_front,
                        "back": new_back,
                        "enable_write": enable_write,
                        "enable_choice": enable_choice,
                        "distractors": distractors_list
                    })
                    save_deck(st.session_state.username, st.session_state.deck_data)
                    st.success(f"Card added to {st.session_state.active_list}!")
                    st.rerun()

        st.subheader(f"Cards in '{st.session_state.active_list}'")
        for i, card in enumerate(current_deck):
            with st.expander(f"{i+1}. {card['front']}"):
                st.write(f"**Answer:** {card['back']}")
                modes = ["Flip"]
                if card.get("enable_write"): modes.append("Type")
                if card.get("enable_choice"): modes.append("Quiz")
                st.caption(f"Modes: {', '.join(modes)}")
                if card.get("distractors"):
                     st.write(f"**Distractors:** {', '.join(card['distractors'])}")
                     
                if st.button("Delete Card", key=f"del_{card['id']}"):
                    st.session_state.deck_data[st.session_state.active_list].pop(i)
                    save_deck(st.session_state.username, st.session_state.deck_data)
                    st.rerun()
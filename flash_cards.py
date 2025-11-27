import streamlit as st
import json
import os

# --- Constants & Config ---
DECK_FILE = "vibe_deck.json"
st.set_page_config(page_title="Vibe Cards", page_icon="⚡", layout="centered")

# --- Helper Functions ---
def load_deck():
    if os.path.exists(DECK_FILE):
        with open(DECK_FILE, "r") as f:
            return json.load(f)
    return [
        {"id": 1, "front": "Welcome to Vibe Cards (Python)", "back": "Streamlit makes Python apps easy!"},
        {"id": 2, "front": "How do you run this?", "back": "Type 'streamlit run flashcards.py' in your terminal."},
        {"id": 3, "front": "List vs Tuple", "back": "Lists are mutable [], Tuples are immutable ()."},
    ]

def save_deck(deck):
    with open(DECK_FILE, "w") as f:
        json.dump(deck, f)

# --- State Management (React-like useState) ---
if "deck" not in st.session_state:
    st.session_state.deck = load_deck()
if "current_index" not in st.session_state:
    st.session_state.current_index = 0
if "is_flipped" not in st.session_state:
    st.session_state.is_flipped = False

# --- UI Styling (Custom CSS for the 'Vibe') ---
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

# --- App Header ---
col1, col2 = st.columns([1, 4])
with col1:
    st.markdown("## ⚡ **Vibe**")
with col2:
    mode = st.radio("Mode", ["Study", "Editor"], horizontal=True, label_visibility="collapsed")

st.divider()

# --- MODE: STUDY ---
if mode == "Study":
    if not st.session_state.deck:
        st.info("No cards left! Go to Editor to create some.")
    else:
        # Get current card
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
                "id": len(st.session_state.deck) + 100, # simple unique id
                "front": new_front,
                "back": new_back
            })
            save_deck(st.session_state.deck)
            st.success("Card added!")
            st.rerun()

    st.subheader("Your Deck")
    for i, card in enumerate(st.session_state.deck):
        with st.expander(f"{i+1}. {card['front']}"):
            st.write(f"**Answer:** {card['back']}")
            if st.button("Delete", key=f"del_{card['id']}"):
                st.session_state.deck.pop(i)
                save_deck(st.session_state.deck)
                # Adjust index if needed
                if st.session_state.current_index >= len(st.session_state.deck):
                    st.session_state.current_index = max(0, len(st.session_state.deck) - 1)
                st.rerun()

    if st.button("Export Deck to JSON"):
        json_str = json.dumps(st.session_state.deck, indent=2)
        st.download_button(
            label="Download JSON",
            data=json_str,
            file_name="vibe_deck.json",
            mime="application/json"
        )
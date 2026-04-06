"""
StreamLens — Streamlit Frontend
Modern, context-aware movie recommendation explorer with user profiling.
"""

import streamlit as st
import pandas as pd
import requests
import json
from pathlib import Path
from datetime import datetime

def _html(html_str: str):
    """Render HTML via st.markdown, stripping leading whitespace from every line
    to prevent Streamlit's markdown parser from treating indented HTML as code blocks."""
    lines = html_str.split("\n")
    cleaned = "\n".join(line.lstrip() for line in lines)
    st.markdown(cleaned, unsafe_allow_html=True)


# ── Config ────────────────────────────────────────────────────────────────
API_BASE = "http://localhost:8000"
VIS_PATH = Path(__file__).parent.parent / "visualizations" / "eda"

st.set_page_config(
    page_title="StreamLens",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)




# ── Helpers ───────────────────────────────────────────────────────────────

def api_get(path: str, params: dict = None):
    try:
        r = requests.get(f"{API_BASE}{path}", params=params, timeout=60)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to the API — make sure FastAPI is running on port 8000.")
        return None
    except requests.exceptions.HTTPError as e:
        try:
            detail = e.response.json().get('detail', str(e))
        except Exception:
            detail = str(e)
        st.error(f"API error: {detail}")
        return None


def api_post(path: str, body: dict):
    try:
        r = requests.post(f"{API_BASE}{path}", json=body, timeout=60)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to the API — make sure FastAPI is running on port 8000.")
        return None
    except requests.exceptions.HTTPError as e:
        try:
            detail = e.response.json().get('detail', str(e))
        except Exception:
            detail = str(e)
        st.error(f"API error: {detail}")
        return None


def detect_time_of_day() -> str:
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "morning"
    elif 12 <= hour < 17:
        return "afternoon"
    elif 17 <= hour < 22:
        return "evening"
    else:
        return "late_night"


GENRE_COLORS = {
    "Action": "#ff6b6b", "Adventure": "#ffa502", "Animation": "#7bed9f",
    "Children": "#70a1ff", "Comedy": "#fdcb6e", "Crime": "#e17055",
    "Documentary": "#00cec9", "Drama": "#a29bfe", "Fantasy": "#fd79a8",
    "Film-Noir": "#636e72", "Horror": "#d63031", "Musical": "#e84393",
    "Mystery": "#6c5ce7", "Romance": "#ff6b81", "Sci-Fi": "#74b9ff",
    "Thriller": "#e17055", "War": "#b2bec3", "Western": "#f9ca24",
    "IMAX": "#00b894",
}


def genre_badge(genre: str) -> str:
    color = GENRE_COLORS.get(genre.strip(), "#636e72")
    r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
    return (
        f'<span style="display:inline-block;padding:4px 12px;margin:2px 6px 6px 0;'
        f'border-radius:20px;font-size:10px;font-weight:700;letter-spacing:0.04em;text-transform:uppercase;'
        f'background:rgba({r},{g},{b},0.12);color:{color};">{genre.strip()}</span>'
    )


def genre_badges(genres_str: str) -> str:
    if not genres_str or genres_str == "nan":
        return ""
    genres = genres_str.replace("|", ",").split(",")
    return " ".join(genre_badge(g) for g in genres if g.strip())


def score_bar(value: float, max_val: float = 1.0, label: str = "Score") -> str:
    pct = min(value / max_val * 100, 100)
    return (
        f'<div style="margin-top:auto;padding-top:24px;">'
        f'<div style="width:100%;height:6px;background:#f1f5f9;border-radius:999px;overflow:hidden;">'
        f'<div style="height:100%;width:{pct}%;background:linear-gradient(to right,#7C3AED,#06B6D4);"></div>'
        f'</div></div>'
    )


def render_movie_cards(movies: list, card_style: str = "recommendation"):
    if not movies:
        st.info("No movies found.")
        return

    cols = st.columns(4)
    for i, movie in enumerate(movies):
        with cols[i % 4]:
            mid = movie["movieId"]
            title = movie["title"]
            genres = genre_badges(" · ".join([g for g in movie.get("genres", []) if g]))
            poster_url = movie.get("poster_url")
            
            poster_html = ""
            if poster_url:
                poster_html = f'<img src="{poster_url}" style="width:100%;border-radius:8px;margin-bottom:8px;"/>'
            else:
                poster_html = f'<div style="width:100%;aspect-ratio:2/3;background:#334155;border-radius:8px;margin-bottom:8px;display:flex;align-items:center;justify-content:center;color:#94a3b8;font-size:12px;">No Image</div>'

            score_html = ""
            if "score" in movie:
                pct = int(movie["score"] * 100)
                score_html = f'<div style="margin-top:8px;font-size:12px;color:#a29bfe;font-weight:700;">{pct}% Match</div>'
            elif "avg_rating" in movie:
                stars = "★" * int(round(movie["avg_rating"])) + "☆" * (5 - int(round(movie["avg_rating"])))
                score_html = f'<div style="margin-top:8px;font-size:13px;color:#fdcb6e;">{stars} <span style="color:#e8eaf0;">({movie["avg_rating"]:.1f})</span></div>'

            _html(f'''
            <div style="background:#1e293b;border-radius:12px;padding:12px;margin-bottom:16px;min-height:300px;display:flex;flex-direction:column;">
                {poster_html}
                <div style="font-size:16px;font-weight:700;color:#e8eaf0;line-height:1.2;margin-bottom:4px;">{title}</div>
                <div>{genres}</div>
                {score_html}
            </div>
            ''')
# ── Session State Init ────────────────────────────────────────────────────

if "profile" not in st.session_state:
    st.session_state.profile = None

if "ratings" not in st.session_state:
    st.session_state.ratings = {}  # {movieId: {"title": ..., "rating": ..., "genres": ...}}

if "context" not in st.session_state:
    st.session_state.context = {
        "time_of_day": detect_time_of_day(),
        "social": "alone",
        "mood": "relaxed",
    }

# Pagination state for "Show More"
if "pers_results" not in st.session_state:
    st.session_state.pers_results = []   # cached personalised recommendations
if "pers_show" not in st.session_state:
    st.session_state.pers_show = 10      # how many to display

if "top_results" not in st.session_state:
    st.session_state.top_results = []    # cached top-rated results
if "top_show" not in st.session_state:
    st.session_state.top_show = 10


# ══════════════════════════════════════════════════════════════════════════
# PROFILE SETUP (shown on first visit)
# ══════════════════════════════════════════════════════════════════════════

if st.session_state.profile is None:
    # Full-page profile setup
    _html("""
    <div style="text-align:center;padding:40px 0 20px;">
        <div style="font-size:56px;margin-bottom:12px;">🎬</div>
        <div style="font-size:42px;font-weight:900;letter-spacing:-0.03em;
                    background:linear-gradient(135deg, #6c5ce7 0%, #a29bfe 40%, #74b9ff 100%);
                    -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                    background-clip:text;line-height:1.2;">
            Welcome to StreamLens
        </div>
        <div style="font-size:16px;color:#5a5e72;margin-top:8px;font-weight:400;">
            Let's set up your profile to personalise your recommendations
        </div>
    </div>
    """)

    st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)

    # Setup form inside a styled container
    _html("""
    <div style="background:rgba(20,20,35,0.6);backdrop-filter:blur(12px);
                border:1px solid rgba(255,255,255,0.06);border-radius:20px;
                padding:32px 28px;max-width:700px;margin:0 auto;">
        <div style="font-size:18px;font-weight:700;color:#e8eaf0;margin-bottom:4px;">
            👤 About You
        </div>
        <div style="font-size:13px;color:#5a5e72;margin-bottom:20px;">
            This helps us recommend movies that match your taste
        </div>
    </div>
    """)

    # Name
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Your name", placeholder="What should we call you?")
    with col2:
        age_group = st.selectbox("Age range", [
            "Under 18", "18-24", "25-34", "35-44", "45-54", "55+",
        ], index=1)

    st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)

    # Fetch genres from API
    genres_data = api_get("/movies/genres")
    available_genres = genres_data.get("genres", []) if genres_data else [
        "Action", "Adventure", "Animation", "Comedy", "Crime", "Documentary",
        "Drama", "Fantasy", "Horror", "Musical", "Mystery", "Romance",
        "Sci-Fi", "Thriller", "War", "Western",
    ]

    _html("""
    <div style="font-size:14px;font-weight:600;color:#a29bfe;margin-bottom:4px;">
        🎭 Pick your favourite genres
    </div>
    <div style="font-size:12px;color:#5a5e72;margin-bottom:8px;">
        Select at least 2 genres you enjoy
    </div>
    """)

    preferred_genres = st.multiselect(
        "Favourite genres",
        available_genres,
        default=["Action", "Sci-Fi", "Comedy"],
        label_visibility="collapsed",
    )

    st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)

    # Context section
    _html("""
    <div style="font-size:14px;font-weight:600;color:#74b9ff;margin-bottom:4px;">
        🎯 What are you looking for right now?
    </div>
    <div style="font-size:12px;color:#5a5e72;margin-bottom:8px;">
        Tell us your current vibe — we'll tailor recommendations to match
    </div>
    """)

    c1, c2, c3 = st.columns(3)
    with c1:
        current_time = detect_time_of_day()
        time_labels = {
            "morning": "🌅 Morning",
            "afternoon": "☀️ Afternoon",
            "evening": "🌆 Evening",
            "late_night": "🌙 Late Night",
        }
        time_options = list(time_labels.keys())
        time_idx = time_options.index(current_time)
        time_of_day = st.selectbox(
            "Time of day",
            time_options,
            index=time_idx,
            format_func=lambda x: time_labels[x],
        )
    with c2:
        social = st.selectbox("Watching with", [
            "alone", "friends", "date", "family",
        ], format_func=lambda x: {
            "alone": "🧑 Solo",
            "friends": "👥 Friends",
            "date": "💑 Date Night",
            "family": "👨‍👩‍👧‍👦 Family",
        }[x])
    with c3:
        mood = st.selectbox("Current mood", [
            "relaxed", "adventurous", "intense", "thoughtful",
        ], format_func=lambda x: {
            "relaxed": "😌 Relaxed",
            "adventurous": "🚀 Adventurous",
            "intense": "🔥 Intense",
            "thoughtful": "🤔 Thoughtful",
        }[x])

    st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)

    if st.button("🚀  Let's Go!", type="primary", use_container_width=True):
        if len(preferred_genres) < 2:
            st.warning("Please select at least 2 genres.")
        else:
            st.session_state.profile = {
                "name": name or "Movie Fan",
                "age_group": age_group,
                "preferred_genres": preferred_genres,
            }
            st.session_state.context = {
                "time_of_day": time_of_day,
                "social": social,
                "mood": mood,
            }
            st.rerun()

    st.stop()


# ══════════════════════════════════════════════════════════════════════════
# MAIN APP  (profile has been set up)
# ══════════════════════════════════════════════════════════════════════════

profile = st.session_state.profile
ctx = st.session_state.context
ratings = st.session_state.ratings


with st.sidebar:
    st.title("🎬 StreamLens")
    st.markdown(f"**Hi, {profile['name']}**")
    st.markdown("---")
    page = st.radio("Navigation", ["🎯 For You", "🔍 Browse", "⭐ Rate Movies"])
    
    st.markdown("---")
    st.markdown("### 🎯 Context Filter")
    
    ctx_time = st.selectbox("Time of Day", ["morning", "afternoon", "evening", "late_night"],
        index=["morning", "afternoon", "evening", "late_night"].index(ctx["time_of_day"]),
        format_func=lambda x: {"morning": "🌅 Morning", "afternoon": "☀️ Afternoon",
                                "evening": "🌆 Evening", "late_night": "🌙 Late Night"}[x],
        key="ctx_time")
    
    ctx_social = st.selectbox("Social Setting", ["alone", "friends", "date", "family"],
        index=["alone", "friends", "date", "family"].index(ctx["social"]),
        format_func=lambda x: {"alone": "🧑 Solo", "friends": "👥 Friends",
                                "date": "💑 Date Night", "family": "👨‍👩‍👧‍👦 Family"}[x],
        key="ctx_social")
        
    ctx_mood = st.selectbox("Current Mood", ["relaxed", "adventurous", "intense", "thoughtful"],
        index=["relaxed", "adventurous", "intense", "thoughtful"].index(ctx["mood"]),
        format_func=lambda x: {"relaxed": "😌 Relaxed", "adventurous": "🚀 Adventurous",
                                "intense": "🔥 Intense", "thoughtful": "🤔 Thoughtful"}[x],
        key="ctx_mood")

    st.session_state.context = {
        "time_of_day": ctx_time,
        "social": ctx_social,
        "mood": ctx_mood,
    }

    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #5a5e72; font-size: 12px; margin-top: 20px;'>"
        "Powered by <b>StreamLens Engine</b><br>"
        "v1.0.0"
        "</div>",
        unsafe_allow_html=True
    )


def render_page_header(title: str, subtitle: str, icon: str = ""):
    _html(f"""
    <div style="background:rgba(20,20,35,0.6);border:1px solid rgba(255,255,255,0.06);border-radius:16px;padding:24px 32px;margin-bottom:32px;box-shadow:0 8px 32px rgba(0,0,0,0.04);backdrop-filter:blur(20px);">
        <div style="font-size:36px;font-weight:900;letter-spacing:-0.02em;color:#e8eaf0;display:flex;align-items:center;gap:12px;">
            <div style="width:28px;height:28px;background:#e8eaf0;border-radius:50%;position:relative;">
                <div style="position:absolute;bottom:-2px;left:-2px;width:10px;height:10px;background:#e8eaf0;border-radius:50%;"></div>
            </div>
            {title}
        </div>
        <div style="font-size:13px;color:rgba(232,234,240,0.6);margin-top:2px;font-weight:500;">{subtitle}</div>
    </div>""")


def render_stat_card(label: str, value: str, icon: str, color: str = "#6c5ce7"):
    r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
    return f"""
    <div style="background:rgba({r},{g},{b},0.08);border:1px solid rgba({r},{g},{b},0.18);
                border-radius:12px;padding:14px 16px;text-align:center;">
        <div style="font-size:22px;margin-bottom:4px;">{icon}</div>
        <div style="font-size:20px;font-weight:800;color:{color};">{value}</div>
        <div style="font-size:11px;font-weight:600;color:#5a5e72;text-transform:uppercase;
                    letter-spacing:0.06em;margin-top:2px;">{label}</div>
    </div>"""


# ── Helper to build the personalised request ──────────────────────────────

def get_personalized_recs(top_k: int = 50):
    """Call the personalized endpoint with current profile + context + ratings.
    Fetches a larger batch so we can paginate locally with Show More."""
    rated_movies = [
        {"movieId": mid, "rating": info["rating"]}
        for mid, info in st.session_state.ratings.items()
    ]
    body = {
        "preferred_genres": profile["preferred_genres"],
        "age_group": profile["age_group"],
        "context": st.session_state.context,
        "rated_movies": rated_movies,
        "top_k": top_k,
    }
    return api_post("/recommendations/personalized", body)


# ══════════════════════════════════════════════════════════════════════════
# PAGE: FOR YOU
# ══════════════════════════════════════════════════════════════════════════

if page == "🎯 For You":
    render_page_header("For You", f"Personalised picks for {profile['name']}", "🎯")

    # Show active context chips
    time_emoji = {"morning": "🌅", "afternoon": "☀️", "evening": "🌆", "late_night": "🌙"}
    social_emoji = {"alone": "🧑", "friends": "👥", "date": "💑", "family": "👨‍👩‍👧‍👦"}
    mood_emoji = {"relaxed": "😌", "adventurous": "🚀", "intense": "🔥", "thoughtful": "🤔"}

    ctx = st.session_state.context
    chips = " ".join([
        f'<span style="display:inline-flex;align-items:center;padding:4px 12px;border-radius:20px;font-size:10px;'
        f'font-weight:700;background:#F5F3FF;color:#7C3AED;margin-bottom:12px;'
        f'margin-right:8px;box-shadow:0 2px 4px rgba(124,58,237,0.05);">'
        f'<span style="font-size:12px;margin-right:4px;">{emoji}</span> {label}</span>'
        for emoji, label in [
            (time_emoji.get(ctx["time_of_day"], ""), ctx["time_of_day"].replace("_", " ").title()),
            (social_emoji.get(ctx["social"], ""), ctx["social"].title()),
            (mood_emoji.get(ctx["mood"], ""), ctx["mood"].title()),
        ]
    ])
    genre_chips = " ".join([genre_badge(g) for g in profile["preferred_genres"]])

    _html(f"""
    <div style="margin-bottom:20px;">
        <div style="margin-bottom:8px;">{chips}</div>
        <div>{genre_chips}</div>
    </div>
    """)

    tab1, tab2 = st.tabs(["✨  Personalised", "🏆  Top Rated"])

    with tab1:
        st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)

        if st.button("✨  Get Personalised Recommendations", type="primary", use_container_width=True):
            with st.spinner("Crafting your personalised picks..."):
                data = get_personalized_recs(top_k=50)
            if data:
                st.session_state.pers_results = data.get("recommendations", [])
                st.session_state.pers_show = 10

        recs = st.session_state.pers_results
        if recs:
            n_rated = len(st.session_state.ratings)
            hint = f" • Influenced by your {n_rated} rated movies" if n_rated > 0 else ""
            showing = min(st.session_state.pers_show, len(recs))

            _html(f"""
            <div style="display:flex;align-items:center;justify-content:space-between;padding:12px 16px;
                        background:#f6f0fa;border:1px solid rgba(157,43,238,0.1);
                        border-radius:12px;margin:12px 0 20px;">
                <div style="display:flex;align-items:center;gap:10px;">
                    <span style="font-size:16px;">✨</span>
                    <span style="font-size:11px;color:#7C3AED;font-weight:700;letter-spacing:0.02em;">
                        Showing {showing} of {len(recs)} picks for you{hint}
                    </span>
                </div>
            </div>
            """)
            render_movie_cards(recs[:showing])

            # Show More button
            if showing < len(recs):
                st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)
                if st.button("⬇️  Show More", key="pers_more", use_container_width=True):
                    st.session_state.pers_show += 10
                    st.rerun()

    with tab2:
        st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            sort_by = st.selectbox("Sort by", ["popularity", "rating"], format_func=lambda x: {
                "popularity": "🔥 Most Popular", "rating": "⭐ Highest Rated",
            }[x])
        with col2:
            min_ratings = st.number_input("Min Ratings", min_value=1, value=50, step=10)

        if st.button("📊  Load Rankings", type="primary", use_container_width=True):
            with st.spinner("Crunching numbers..."):
                data = api_get("/recommendations/top", {"top_k": 50, "min_ratings": min_ratings, "sort_by": sort_by})
            if data:
                st.session_state.top_results = data.get("movies", [])
                st.session_state.top_show = 10

        movies_list = st.session_state.top_results
        if movies_list:
            showing = min(st.session_state.top_show, len(movies_list))
            visible = movies_list[:showing]

            avg_rating = sum(m.get("avg_rating", 0) for m in visible) / len(visible)
            total_ratings = sum(m.get("num_ratings", 0) for m in visible)
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(render_stat_card("Showing", f"{showing} of {len(movies_list)}", "🎬", "#6c5ce7"), unsafe_allow_html=True)
            with c2:
                st.markdown(render_stat_card("Avg Rating", f"{avg_rating:.2f}", "⭐", "#fdcb6e"), unsafe_allow_html=True)
            with c3:
                st.markdown(render_stat_card("Total Ratings", f"{total_ratings:,}", "📊", "#74b9ff"), unsafe_allow_html=True)
            st.markdown('<div style="height:20px;"></div>', unsafe_allow_html=True)

            render_movie_cards(visible, card_style="top")

            # Show More button
            if showing < len(movies_list):
                st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)
                if st.button("⬇️  Show More", key="top_more", use_container_width=True):
                    st.session_state.top_show += 10
                    st.rerun()


# ══════════════════════════════════════════════════════════════════════════
# PAGE: BROWSE
# ══════════════════════════════════════════════════════════════════════════

elif page == "🔍 Browse":
    render_page_header("Browse Movies", "Explore the complete catalogue", "🔍")

    query = st.text_input("🔎  Search by title", placeholder="e.g. Matrix, Inception, Star Wars...")

    if query:
        results = api_get("/movies/search", {"q": query, "limit": 20})
        if results:
            movies_list = results.get("movies", [])
            _html(f"""
            <div style="font-size:13px;color:#5a5e72;margin:8px 0 16px;font-weight:500;">
                Found <span style="color:#74b9ff;font-weight:700;">{results['count']}</span> results
            </div>
            """)

            if movies_list:
                df = pd.DataFrame(movies_list)
                selected_title = st.selectbox("Select a movie for details", df["title"].tolist())
                selected_id = df[df["title"] == selected_title]["movieId"].iloc[0]

                detail = api_get(f"/movies/{selected_id}")
                if detail:
                    st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)
                    genres_html = genre_badges(" · ".join(detail.get("genres", [])))
                    has_stats = "avg_rating" in detail

                    stats_html = ""
                    if has_stats:
                        avg = detail['avg_rating']
                        stars = "★" * int(round(avg)) + "☆" * (5 - int(round(avg)))
                        stats_html = f"""
                        <div style="display:flex;gap:24px;margin-top:16px;padding-top:16px;
                                    border-top:1px solid rgba(255,255,255,0.06);">
                            <div>
                                <div style="font-size:11px;font-weight:600;color:#5a5e72;text-transform:uppercase;letter-spacing:0.06em;">Rating</div>
                                <div style="display:flex;align-items:center;gap:6px;margin-top:4px;">
                                    <span style="font-size:16px;color:#fdcb6e;">{stars}</span>
                                    <span style="font-size:18px;font-weight:800;color:#e8eaf0;">{avg:.1f}</span>
                                </div>
                            </div>
                            <div>
                                <div style="font-size:11px;font-weight:600;color:#5a5e72;text-transform:uppercase;letter-spacing:0.06em;">Reviews</div>
                                <div style="font-size:18px;font-weight:800;color:#e8eaf0;margin-top:4px;">{detail['num_ratings']:,}</div>
                            </div>
                        </div>"""

                    _html(f"""
                    <div class="sl-detail" style="background:rgba(20,20,35,0.6);backdrop-filter:blur(12px);
                                border:1px solid rgba(255,255,255,0.06);border-radius:16px;padding:24px 28px;">
                        <div style="font-size:24px;font-weight:800;color:#e8eaf0;letter-spacing:-0.01em;
                                    line-height:1.3;margin-bottom:12px;">{detail['title']}</div>
                        <div>{genres_html}</div>
                        {stats_html}
                    </div>
                    """)

                    # Quick rate from browse
                    st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)
                    existing_rating = ratings.get(int(selected_id), {}).get("rating", 0.0)
                    rate_val = st.slider(
                        f"Rate {detail['title']}",
                        0.5, 5.0,
                        value=existing_rating if existing_rating > 0 else 3.0,
                        step=0.5,
                        key=f"browse_rate_{selected_id}",
                    )
                    if st.button("⭐  Save Rating", type="primary", key=f"browse_save_{selected_id}"):
                        st.session_state.ratings[int(selected_id)] = {
                            "title": detail["title"],
                            "rating": rate_val,
                            "genres": "|".join(detail.get("genres", [])),
                        }
                        st.success(f"Rated **{detail['title']}** → {rate_val} ⭐")


# ══════════════════════════════════════════════════════════════════════════
# PAGE: RATE MOVIES
# ══════════════════════════════════════════════════════════════════════════

elif page == "⭐ Rate Movies":
    render_page_header("Rate Movies", "Rate movies you've watched to improve your recommendations", "⭐")

    tab_rate, tab_history = st.tabs(["🔎  Find & Rate", "📋  Your Ratings"])

    with tab_rate:
        st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)

        search_q = st.text_input("Search for a movie to rate", placeholder="e.g. Interstellar, The Dark Knight...", key="rate_search")

        if search_q:
            results = api_get("/movies/search", {"q": search_q, "limit": 10})
            if results and results.get("movies"):
                for movie in results["movies"]:
                    mid = movie["movieId"]
                    genres_html = genre_badges(movie.get("genres", ""))
                    existing = ratings.get(mid, {}).get("rating")
                    already_rated = "✅" if existing else ""

                    border_alpha = '0.15' if existing else '0.06'
                    _html(f"""
                    <div class="sl-rate-card" style="background:rgba(20,20,35,0.5);backdrop-filter:blur(12px);
                                border:1px solid rgba(255,255,255,{border_alpha});
                                border-radius:12px;padding:14px 18px;margin-bottom:10px;">
                        <div style="display:flex;justify-content:space-between;align-items:center;">
                            <div>
                                <span style="font-size:14px;font-weight:700;color:#e8eaf0;">{movie['title']}</span>
                                <span style="font-size:13px;margin-left:6px;">{already_rated}</span>
                            </div>
                            <span style="font-size:11px;color:#5a5e72;">ID: {mid}</span>
                        </div>
                        <div style="margin-top:6px;">{genres_html}</div>
                    </div>
                    """)

                    col1, col2 = st.columns([3, 1])
                    with col1:
                        rate_val = st.slider(
                            f"Rate",
                            0.5, 5.0,
                            value=existing if existing else 3.0,
                            step=0.5,
                            key=f"rate_{mid}",
                            label_visibility="collapsed",
                        )
                    with col2:
                        btn_label = "Update" if existing else "Rate"
                        if st.button(f"⭐ {btn_label}", key=f"save_{mid}", use_container_width=True):
                            st.session_state.ratings[mid] = {
                                "title": movie["title"],
                                "rating": rate_val,
                                "genres": movie.get("genres", ""),
                            }
                            st.success(f"{'Updated' if existing else 'Rated'} **{movie['title']}** → {rate_val} ⭐")
                            st.rerun()

    with tab_history:
        st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)

        if not ratings:
            _html("""
            <div style="text-align:center;padding:40px 20px;color:#5a5e72;">
                <div style="font-size:48px;margin-bottom:12px;">⭐</div>
                <div style="font-size:16px;font-weight:600;color:#8b8fa3;">No ratings yet</div>
                <div style="font-size:13px;margin-top:4px;">Search and rate movies to improve your recommendations</div>
            </div>
            """)
        else:
            # Summary
            avg_user_rating = sum(r["rating"] for r in ratings.values()) / len(ratings)
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(render_stat_card("Movies Rated", str(len(ratings)), "🎬", "#6c5ce7"), unsafe_allow_html=True)
            with c2:
                st.markdown(render_stat_card("Avg Rating", f"{avg_user_rating:.1f}", "⭐", "#fdcb6e"), unsafe_allow_html=True)

            st.markdown('<div style="height:20px;"></div>', unsafe_allow_html=True)

            # List rated movies
            sorted_ratings = sorted(ratings.items(), key=lambda x: x[1]["rating"], reverse=True)
            for mid, info in sorted_ratings:
                stars = "★" * int(round(info["rating"])) + "☆" * (5 - int(round(info["rating"])))
                genres_html = genre_badges(info.get("genres", ""))

                _html(f"""
                <div style="background:rgba(20,20,35,0.5);border:1px solid rgba(255,255,255,0.06);
                            border-radius:12px;padding:14px 18px;margin-bottom:8px;
                            display:flex;justify-content:space-between;align-items:center;">
                    <div>
                        <div style="font-size:14px;font-weight:700;color:#e8eaf0;margin-bottom:4px;">
                            {info['title']}
                        </div>
                        <div>{genres_html}</div>
                    </div>
                    <div style="text-align:right;min-width:80px;">
                        <div style="font-size:16px;color:#fdcb6e;">{stars}</div>
                        <div style="font-size:14px;font-weight:800;color:#e8eaf0;">{info['rating']}</div>
                    </div>
                </div>
                """)

            st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)
            if st.button("🗑️  Clear All Ratings", use_container_width=True):
                st.session_state.ratings = {}
                st.rerun()

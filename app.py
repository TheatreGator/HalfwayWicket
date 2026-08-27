import random
import requests
import streamlit as st
from geopy.distance import geodesic
from geopy.geocoders import Nominatim

# Initialize Geolocator
geolocator = Nominatim(user_agent="halfway_wicket_app")

# Page Configuration & Cricket Theming CSS
st.set_page_config(
    page_title="Halfway Wicket | Fair Cricket Ground & Pub Finder",
    page_icon="🏏",
    layout="wide",
)

st.markdown(
    """
    <style>
    /* Main Theme Background and Colors */
    .stApp {
        background-color: #0b2e13;
        color: #f8f9fa;
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #f4d03f !important;
        font-family: 'Helvetica Neue', sans-serif;
    }
    
    /* Containers & Cards */
    div.stMarkdown {
        color: #e2e8f0;
    }
    
    /* Custom Metric/Result Cards */
    .metric-card {
        background-color: #143d20;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #f4d03f;
        margin-bottom: 15px;
    }
    
    /* Buttons */
    .stButton>button {
        background-color: #f4d03f;
        color: #0b2e13;
        font-weight: bold;
        border-radius: 8px;
        border: none;
        padding: 0.6rem 1.2rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
    }
    .stButton>button:hover {
        background-color: #d4ac0d;
        color: #0b2e13;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=3600)
def get_coordinates(location_str):
  try:
    loc = geolocator.geocode(location_str)
    if loc:
      return (loc.latitude, loc.longitude), loc.address
  except Exception:
    pass
  return None, None


@st.cache_data(ttl=3600)
def find_amenities_near_point(lat, lon, amenity_type, radius=8000):
  overpass_url = "http://overpass-api.de/api/interpreter"
  query = f"""
    [out:json][timeout:25];
    (
      node["amenity"="{amenity_type}"](around:{radius},{lat},{lon});
      way["amenity"="{amenity_type}"](around:{radius},{lat},{lon});
    );
    out body;
    >;
    out skel qt;
    """
  try:
    response = requests.get(overpass_url, params={"data": query}, timeout=10)
    if response.status_code == 200:
      data = response.json()
      elements = []
      for element in data.get("elements", []):
        name = element.get("tags", {}).get("name")
        el_lat = element.get("lat") or element.get("center", {}).get("lat")
        el_lon = element.get("lon") or element.get("center", {}).get("lon")
        if name and el_lat and el_lon:
          elements.append({"name": name, "lat": el_lat, "lon": el_lon})
      return elements
  except Exception:
    pass
  return []


# App Header
st.title("🏏 Halfway Wicket")
st.markdown(
    "### Find the fairest cricket pitch meeting point between two locations,"
    " complete with local pubs along the route!"
)

# Popular presets for quick searching & autocomplete simulation
preset_locations = [
    "London, UK",
    "Bristol, UK",
    "Birmingham, UK",
    "Manchester, UK",
    "Leeds, UK",
    "Nottingham, UK",
    "Southampton, UK",
    "Cardiff, UK",
    "Sheffield, UK",
    "Leicester, UK",
]

col1, col2 = st.columns(2)
with col1:
  st.markdown("#### Player 1 Start")
  loc1_input = st.selectbox(
      "Choose or type City/Postcode",
      options=preset_locations,
      index=0,
      key="p1_select",
  )
  custom_loc1 = st.text_input(
      "Or type custom Postcode/City 1", "", key="p1_custom"
  )
  final_loc1 = custom_loc1 if custom_loc1.strip() else loc1_input

with col2:
  st.markdown("#### Player 2 Start")
  loc2_input = st.selectbox(
      "Choose or type City/Postcode",
      options=preset_locations,
      index=1,
      key="p2_select",
  )
  custom_loc2 = st.text_input(
      "Or type custom Postcode/City 2", "", key="p2_custom"
  )
  final_loc2 = custom_loc2 if custom_loc2.strip() else loc2_input

if st.button("Calculate Fairest Wicket & Pubs", type="primary"):
  with st.spinner(
      "Scanning regional corridors and cricket infrastructure..."
  ):
    coords1, addr1 = get_coordinates(final_loc1)
    coords2, addr2 = get_coordinates(final_loc2)

    if not coords1 or not coords2:
      st.error(
          "Could not resolve one or both locations. Please try entering a valid"
          " city name."
      )
    else:
      total_dist = geodesic(coords1, coords2).kilometers

      # Calculate Corridor midpoint and bounding box center
      mid_lat = (coords1[0] + coords2[0]) / 2
      mid_lon = (coords1[1] + coords2[1]) / 2

      st.success(
          f"**Journey Span:** {addr1} ➔ {addr2} (Total Straight-line:"
          f" {int(total_dist)} km)"
      )

      # Search for cricket grounds within a wide box or radius covering the corridor
      overpass_url = "http://overpass-api.de/api/interpreter"
      # Search radius covers half the distance or up to 40km around the midpoint
      search_radius = min(max(total_dist * 0.4, 15000), 50000)

      cricket_query = f"""
            [out:json][timeout:25];
            (
              node["sport"="cricket"](around:{search_radius},{mid_lat},{mid_lon});
              way["sport"="cricket"](around:{search_radius},{mid_lat},{mid_lon});
            );
            out body;
            >;
            out skel qt;
            """
      cricket_grounds = []
      try:
        res = requests.get(overpass_url, params={"data": cricket_query}, timeout=12)
        if res.status_code == 200:
          data = res.json()
          for element in data.get("elements", []):
            tags = element.get("tags", {})
            name = tags.get("name") or tags.get("description")
            lat = element.get("lat") or element.get("center", {}).get("lat")
            lon = element.get("lon") or element.get("center", {}).get("lon")
            if name and lat and lon:
              d1 = geodesic(coords1, (lat, lon)).kilometers
              d2 = geodesic(coords2, (lat, lon)).kilometers
              # Fairness metric: difference between travel distances for player 1 and player 2
              fairness_score = abs(d1 - d2)
              cricket_grounds.append({
                  "name": name,
                  "lat": lat,
                  "lon": lon.
                  if isinstance(lon, (int, float))
                  else float(lon),
                  "d1": d1,
                  "d2": d2,
                  "fairness": fairness_score,
              })
      except Exception:
        pass

      st.markdown("---")
      col_res1, col_res2, col_res3 = st.columns(3)

      with col_res1:
        st.subheader("🏟️ Fairest Cricket Grounds")
        if cricket_grounds:
          # Sort by the fairest balance between both players
          cricket_grounds = sorted(
              cricket_grounds, key=lambda x: x["fairness"]
          )[:4]
          for idx, ground in enumerate(cricket_grounds):
            st.markdown(f"""
                        <div class="metric-card">
                            <b>{idx+1}. {ground['name']}</b><br>
                            - From Player 1: {ground['d1']:.1f} km<br>
                            - From Player 2: {ground['d2']:.1f} km<br>
                            - <i>Fairness gap: ±{ground['fairness']:.1f} km</i>
                        </div>
                        """, unsafe_allow_html=True)
          best_ground = cricket_grounds[0]
        else:
          st.info(
              "No specific cricket grounds matched inside the direct corridor."
              " Using general midpoint."
          )
          best_ground = {
              "name": "Central Meeting Point",
              "lat": mid_lat,
              "lon": mid_lon,
              "d1": total_dist / 2,
              "d2": total_dist / 2,
          }

      with col_res2:
        st.subheader("🍻 Pubs Near Ground")
        ground_pubs = find_amenities_near_point(
            best_ground["lat"], best_ground["lon"], "pub", radius=5000
        )
        if ground_pubs:
          for pub in ground_pubs[:4]:
            st.markdown(f"- 🍺 **{pub['name']}**")
        else:
          st.info("No pubs indexed directly next to this pitch.")

      with col_res3:
        st.subheader("🛤️ Pubs Along Route (Player 1 & 2)")
        # Find pubs closer to player 1 and player 2 start points to cover both routes
        p1_pubs = find_amenities_near_point(
            coords1[0], coords1[1], "pub", radius=10000
        )
        p2_pubs = find_amenities_near_point(
            coords2[0], coords2[1], "pub", radius=10000
        )

        st.markdown(f"**Near {addr1.split(',')[0]}:**")
        if p1_pubs:
          for pub in p1_pubs[:2]:
            st.markdown(f"- 🍻 {pub['name']}")
        else:
          st.write("None found nearby.")

        st.markdown(f"**Near {addr2.split(',')[0]}:**")
        if p2_pubs:
          for pub in p2_pubs[:2]:
            st.markdown(f"- 🍻 {pub['name']}")
        else:
          st.write("None found nearby.")

      # Save state for mini-game personalization
      st.session_state["last_loc1"] = addr1.split(",")[0]
      st.session_state["last_loc2"] = addr2.split(",")[0]

# Mini-Game Section
st.markdown("---")
st.subheader("🎮 Custom Mini-Game: The Halfway Pub & Pitch Challenge")

l1_name = st.session_state.get("last_loc1", "Player 1's hometown")
l2_name = st.session_state.get("last_loc2", "Player 2's hometown")

st.markdown(
    f"Test your knowledge customized for your trip from **{l1_name}** to"
    f" **{l2_name}**!"
)

if "score" not in st.session_state:
  st.session_state.score = 0
  st.session_state.q_idx = 0

dynamic_questions = [
    {
        "q": (
            f"If a traveler from {l1_name} and someone from {l2_name} meet for a"
            " match, what traditional post-match drink is historically tied"
            " to English village cricket teas?"
        ),
        "options": [
            "Pimms or traditional bitter ale",
            "Iced matcha green tea lattes",
            "Sparkling coconut water",
        ],
        "answer": 0,
    },
    {
        "q": (
            "When calculating the fairest meeting pitch between regions like"
            f" {l1_name} and {l2_name}, which geometric center formula provides"
            " equal baseline weight?"
        ),
        "options": [
            "The Haversine Midpoint Formula",
            "The Boundary Rope Equation",
            "The LBW Calculator Matrix",
        ],
        "answer": 0,
    },
]

curr_q = dynamic_questions[st.session_state.q_idx % len(dynamic_questions)]

st.write(f"**Question {st.session_state.q_idx + 1}:** {curr_q['q']}")
choice = st.radio(
    "Select your option:", curr_q["options"], key=f"game_q_{st.session_state.q_idx}"
)

if st.button("Check Answer"):
  if curr_q["options"].index(choice) == curr_q["answer"]:
    st.success("Correct! You've successfully defended your wicket 🏏.")
    st.session_state.score += 1
  else:
    st.error("Out! That's incorrect.")
  st.session_state.q_idx += 1
  st.rerun()

st.write(f"**Current Cricket Score:** {st.session_state.score} runs")

import random
import requests
import streamlit as st
from geopy.distance import geodesic
from geopy.geocoders import Nominatim

# Initialize Geolocator
geolocator = Nominatim(user_agent="cricket_ground_finder_app")

st.set_page_config(
    page_title="Midpoint Cricket & Pub Finder", page_icon="🏏", layout="wide"
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
def find_amenities_near_point(lat, lon, amenity_type, radius=5000):
  # Overpass API query for OpenStreetMap
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
    response = requests.get(overpass_url, params={"data": query})
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


# App Layout
st.title("🏏 Midpoint Cricket Ground & Pub Finder")
st.markdown(
    "Enter two locations to find the fairest meeting spot with a cricket pitch"
    " and watering holes nearby."
)

col1, col2 = st.columns(2)
with col1:
  loc1_input = st.text_input(
      "Location 1 (City or Postcode)", "London, UK", key="loc1"
  )
with col2:
  loc2_input = st.text_input(
      "Location 2 (City or Postcode)", "Bristol, UK", key="loc2"
  )

if st.button("Find Meeting Ground", type="primary"):
  with st.spinner("Calculating midpoint and scanning maps..."):
    coords1, addr1 = get_coordinates(loc1_input)
    coords2, addr2 = get_coordinates(loc2_input)

    if not coords1 or not coords2:
      st.error(
          "Could not resolve one or both locations. Please try more specific"
          " city names or valid postcodes."
      )
    else:
      # Calculate Midpoint
      mid_lat = (coords1[0] + coords2[0]) / 2
      mid_lon = (coords1[1] + coords2[1]) / 2
      midpoint = (mid_lat, mid_lon)

      st.success(
          f"**Route Established:** {addr1} ➔ {addr2} (Approx."
          f" {int(geodesic(coords1, coords2).kilometers)} km total)"
      )

      # Search for Cricket Grounds (using leisure=pitch or sport=cricket tags)
      overpass_url = "http://overpass-api.de/api/interpreter"
      cricket_query = f"""
            [out:json][timeout:25];
            (
              node["sport"="cricket"](around:15000,{mid_lat},{mid_lon});
              way["sport"="cricket"](around:15000,{mid_lat},{mid_lon});
              relation["sport"="cricket"](around:15000,{mid_lat},{mid_lon});
            );
            out body;
            >;
            out skel qt;
            """
      cricket_grounds = []
      try:
        res = requests.get(overpass_url, params={"data": cricket_query})
        if res.status_code == 200:
          data = res.json()
          for element in data.get("elements", []):
            tags = element.get("tags", {})
            name = tags.get("name") or tags.get("description")
            lat = element.get("lat") or element.get("center", {}).get("lat")
            lon = element.get("lon") or element.get("center", {}).get("lon")
            if name and lat and lon:
              dist_from_mid = geodesic(midpoint, (lat, lon)).kilometers
              cricket_grounds.append({
                  "name": name,
                  "lat": lat,
                  "lon": lon,
                  "distance": dist_from_mid,
              })
      except Exception:
        pass

      st.markdown("---")
      col_res1, col_res2 = st.columns(2)

      with col_res1:
        st.subheader("🏟️ Recommended Cricket Grounds")
        if cricket_grounds:
          # Sort by distance from midpoint
          cricket_grounds = sorted(
              cricket_grounds, key=lambda x: x["distance"]
          )[:5]
          for ground in cricket_grounds:
            st.markdown(
                f"- **{ground['name']}** (~{ground['distance']:.1f} km from"
                " midpoint)"
            )
          selected_ground = cricket_grounds[0]
        else:
          st.info(
              "No specific cricket grounds found via automated mapping right"
              " near the midpoint. Falling back to regional search bounds."
          )
          selected_ground = {"name": "Midpoint Area General", "lat": mid_lat, "lon": mid_lon}

      with col_res2:
        st.subheader("🍻 Pubs Along the Route / Near Midpoint")
        pubs = find_amenities_near_point(
            selected_ground["lat"],
            selected_ground["lon"],
            "pub",
            radius=8000,
        )
        if pubs:
          for pub in pubs[:5]:
            st.markdown(f"- 🍺 {pub['name']}")
        else:
          st.info("No notable pubs found immediately nearby.")

# Mini-Game Section
st.markdown("---")
st.subheader("🎮 Mini-Game: The Pitch & Pint Quiz")
st.markdown(
    "Can you match the quirky cricket rule with the correct pub terminology?"
)

if "score" not in st.session_state:
  st.session_state.score = 0
  st.session_state.question_index = 0

questions = [
    {
        "q": (
            "What do a cricket 'duck' and a traditional British pub order of"
            " 'bottle of stout' have in common?"
        ),
        "options": [
            "They both trace their origins back to 17th-century royalty",
            "The term 'duck' originally derived from a round-bottomed dark glass bottle shape resembling an egg",
            "Nothing at all, it's just a trick question",
        ],
        "answer": 1,
    },
    {
        "q": (
            "If a match is rained out and everyone retreats to the pub, which"
            " fielding position shares its name with a historical pub game?"
        ),
        "options": ["Silly Mid-Off", "Third Man", "The Boundary"],
        "answer": 0,
    },
]

q_idx = st.session_state.question_index % len(questions)
current_q = questions[q_idx]

st.write(f"**Question {st.session_state.question_index + 1}:** {current_q['q']}")
user_choice = st.radio(
    "Choose your answer:", current_q["options"], key=f"q_{st.session_state.question_index}"
)

if st.button("Submit Answer"):
  selected_idx = current_q["options"].index(user_choice)
  if selected_idx == current_q["answer"]:
    st.success("Spot on! You've earned an imaginary pint 🍺.")
    st.session_state.score += 1
  else:
    st.error("Not quite! Better luck on the next delivery.")
  st.session_state.question_index += 1
  st.rerun()

st.write(f"**Current Score:** {st.session_state.score}")

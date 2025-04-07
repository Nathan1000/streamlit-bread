import streamlit as st
from streamlit_cookies_controller import CookieController
from datetime import time, datetime, timedelta
import time as time2
import json
import openai
import base64
import mimetypes
from streamlit_js_eval import streamlit_js_eval

st.set_page_config(layout="wide")

# Init cookie controller
controller = CookieController()

# Sidebar navigation
st.sidebar.title("Sourdough Baking Assistant")
section = st.sidebar.radio("Go to", [
    "Bake Planner",
    "Starter Log",
    "Hydration Calculator",
    "Troubleshooting"
])

# Header
st.title("Sourdough Bake Planner")

# Bake Planner Section
if section == "Bake Planner":
    st.header("Plan Your Bake")

    # Load cookie values if available
    saved_data = controller.get("bake_inputs")
    values = saved_data if isinstance(saved_data, dict) else json.loads(saved_data) if saved_data else {}

    if values:
        if st.button("Start Again - clear timeline"):
            controller.remove("bake_inputs")
            st.session_state.clear()
            time2.sleep(1)
            st.rerun()

    temp_options = {
        "Cold (<20°C)": 5.0,
        "Moderate (20–24°C)": 4.0,
        "Warm (>24°C)": 3.5
    }

    with st.expander("📝 Input Your Bake Preferences 🍞"):
        with st.form("bake_plan_form"):
            start_time = st.time_input("When are you starting your bake?", value=time.fromisoformat(values.get("start_time", "14:00")))
            cold_proof = st.checkbox("Cold proof overnight (in fridge)?", value=values.get("cold_proof", True))

            flour_type = st.selectbox("Type of Flour", [
                "Strong White",
                "Whole Wheat",
                "50/50 White & Whole Wheat",
                "Rye",
                "Other"
            ], index=["Strong White","Whole Wheat","50/50 White & Whole Wheat","Rye","Other"].index(values.get("flour_type", "Strong White")))

            bake_vessel = st.selectbox("Baking Vessel", [
                "Dutch Oven",
                "Loaf Tin",
                "Baking Tray with Steam",
                "Other"
            ], index=["Dutch Oven","Loaf Tin","Baking Tray with Steam","Other"].index(values.get("bake_vessel", "Dutch Oven")))

            starter_type = st.selectbox("Starter Type", [
                "White Starter",
                "Rye Starter",
                "Whole Wheat Starter",
                "Unknown"
            ], index=["White Starter","Rye Starter","Whole Wheat Starter","Unknown"].index(values.get("starter_type", "White Starter")))

            room_temp = st.selectbox("Room Temperature", list(temp_options.keys()), index=list(temp_options.keys()).index(values.get("room_temp", "Moderate (20–24°C)")))
            default_bulk_hours = temp_options[room_temp]

            bulk_override = st.slider(
                "Adjust Bulk Fermentation Duration (hours)",
                min_value=3.0,
                max_value=6.0,
                value=float(values.get("bulk_override", default_bulk_hours)),
                step=0.5,
                help="You can extend bulk slightly if dough isn’t jiggly or bubbly yet"
            )

            cold_proof_hours = st.slider(
                "Adjust Cold Proof Duration (hours)",
                min_value=6,
                max_value=24,
                value=int(values.get("cold_proof_hours", 10)),
                step=1,
                help="You can shorten or lengthen fridge time depending on your schedule"
            ) if cold_proof else None

            submit = st.form_submit_button("Generate Bake Timeline")

    if submit:
        input_data = {
            "start_time": start_time.isoformat(),
            "cold_proof": cold_proof,
            "flour_type": flour_type,
            "bake_vessel": bake_vessel,
            "starter_type": starter_type,
            "room_temp": room_temp,
            "bulk_override": bulk_override,
            "cold_proof_hours": cold_proof_hours
        }
        controller.set("bake_inputs", json.dumps(input_data), max_age=30*24*60*60)

    active_source = values if not submit else input_data
    if active_source:
        now = datetime.combine(datetime.today(), time.fromisoformat(active_source["start_time"]))
        autolyse_end = now + timedelta(minutes=60)
        bulk_end = autolyse_end + timedelta(hours=float(active_source["bulk_override"]))
        fold_interval = float(active_source["bulk_override"]) * 60 / 3
        fold_times = [autolyse_end + timedelta(minutes=i * fold_interval) for i in range(3)]
        shape_end = bulk_end + timedelta(minutes=30)

        # Highlighting current step
        client_now = streamlit_js_eval(js_expressions="new Date().toISOString()", key="local_time")
        if client_now:
            current_time = datetime.fromisoformat(client_now.replace("Z", "+00:00"))

        def highlight(timepoint, label):
            return f"**:green[{timepoint.strftime('%H:%M')} – {label}]**" if timepoint <= current_time else f"**{timepoint.strftime('%H:%M')}** – {label}"

        cols = st.columns([2, 1])

        with cols[0]:
            st.subheader("Your Bake Schedule")
            st.markdown(highlight(now, "Mix flour & water (Autolyse)"))
            st.markdown(highlight(autolyse_end, "Add starter and salt, begin bulk fermentation"))
            for i, ft in enumerate(fold_times, 1):
                st.markdown(highlight(ft, f"Stretch & fold #{i}"))
            st.markdown(highlight(bulk_end, "End of bulk fermentation"))
            st.markdown(highlight(shape_end, "Shape the dough"))

            if active_source["cold_proof"]:
                next_day = shape_end + timedelta(hours=int(active_source["cold_proof_hours"]))
                preheat_time = next_day
                bake_time = preheat_time + timedelta(minutes=45)
                cool_time = bake_time + timedelta(minutes=45)
                eat_time = cool_time + timedelta(minutes=90)

                st.markdown(highlight(shape_end, "Place in fridge for overnight proof"))
                st.markdown("\n**------- Next Day -------**")
                st.markdown(highlight(preheat_time, "Preheat oven to 250°C with baking vessel inside"))
                st.markdown(highlight(preheat_time + timedelta(minutes=45), "Score and bake: 20 mins with lid, 20–25 mins without"))
                st.markdown(highlight(cool_time, "Remove from oven and leave to cool for at least an hour"))
                st.markdown(highlight(eat_time, "Eat and enjoy!"))
            else:
                warm_proof_end = shape_end + timedelta(hours=3)
                preheat_time = warm_proof_end - timedelta(minutes=45)
                bake_time = warm_proof_end
                cool_time = bake_time + timedelta(minutes=45)
                eat_time = cool_time + timedelta(minutes=90)

                st.markdown(highlight(shape_end, "Start room temp proof (~3 hrs)"))
                st.markdown(highlight(preheat_time, "Preheat oven to 250°C with baking vessel inside"))
                st.markdown(highlight(bake_time, "Score and bake: 20 mins with lid, 20–25 mins without"))
                st.markdown(highlight(cool_time, "Remove from oven and leave to cool for at least an hour"))
                st.markdown(highlight(eat_time, "Eat and enjoy!"))

            st.markdown("---")
            st.subheader("Bake Preferences")
            st.markdown(f"**Flour Type:** {active_source['flour_type']}")
            st.markdown(f"**Bake Vessel:** {active_source['bake_vessel']}")
            st.markdown(f"**Starter Type:** {active_source['starter_type']}")
            st.markdown(f"**Room Temp:** {active_source['room_temp']}")
            st.markdown(f"**Bulk Fermentation Time Adjusted to:** {active_source['bulk_override']} hours")
            if active_source["cold_proof"]:
                st.markdown(f"**Cold Proof Duration:** {active_source['cold_proof_hours']} hours")

        with cols[1]:
            with st.expander("How to fold the dough"):
                st.markdown("""
                1. Wet your hands to prevent sticking.  
                2. Grab one side of the dough, stretch it up gently, and fold it over to the opposite side.  
                3. Rotate the bowl a quarter turn and repeat. Do this four times to complete one full fold.  
                4. Let the dough rest, covered, until the next fold.  
                5. Each fold helps strengthen gluten and develop structure.
                """)

            with st.expander("How to shape the dough"):
                st.markdown("Flip dough seam-side down. Fold edges to center, flip again, and drag to create surface tension.")

            with st.expander("What it should look like at the autolyse stage"):
                st.image("media/autolyse.png", caption="In a perfect world")

            with st.expander("What it should look like after bulk fermentation"):
                st.image("media/post-bulk-ferm.png", caption="In a perfect world")

            with st.expander("What it should look like after proof"):
                st.image("media/perfect-post-proof.png", caption="In a perfect world")

            with st.expander("What it should look like after shaping"):
                st.image("media/shaping.png", caption="In a perfect world")



# Placeholder for other tabs
elif section == "Starter Log":
    st.header("Starter Log")
    st.info("Coming soon...")

elif section == "Hydration Calculator":
    st.header("Hydration Calculator")
    st.info("Coming soon...")

elif section == "Troubleshooting":
    st.header("Troubleshooting Guide")

    if "openai_api_key" not in st.session_state:
        st.session_state["openai_api_key"] = ""

    # Stage selection
    stage = st.selectbox("Which stage are you at?", [
        "Mixing",
        "Autolyse",
        "Bulk Fermentation",
        "Folding",
        "Shaping",
        "Cold Proof",
        "Baking",
        "Post-Bake"
    ], key="selected_stage")

    # Problem selection
    common_issues = {
        "Mixing": ["Dough isn’t coming together", "Dough is crumbly or dry", "Too wet and runny", "Hard to mix evenly"],
        "Autolyse": ["Dough feels stiff after resting", "Very slack or wet", "Still dry/clumpy", "Doesn’t seem to help my dough"],
        "Bulk Fermentation": ["Dough isn’t rising", "Too much rise", "No visible bubbles", "Surface has dried out", "Not sure when to stop"],
        "Folding": ["Dough tears during fold", "Still sticky", "No strength developing", "Dough won’t hold shape"],
        "Shaping": ["Too slack, won’t hold shape", "Sticks to surface/hands", "Tears during shaping", "Not sure it has enough tension"],
        "Cold Proof": ["Didn’t rise in fridge", "Spread out flat", "Formed a dry crust", "Overproofed"],
        "Baking": ["No oven spring", "Crust burst", "Pale crust", "Burned bottom"],
        "Post-Bake": ["Dense or gummy crumb", "No holes", "Weird smell or taste", "Undercooked in middle"]
    }
    issue = st.selectbox("What issue are you having?", common_issues.get(stage, []) + ["Just looking for feedback!"], key="selected_issue")

    # Image upload (live)
    uploaded_image = st.file_uploader("Upload an image of your dough or loaf", type=["jpg", "jpeg", "png"], key="uploaded_image")



    # API key input
    with st.expander("🔐 Enter OpenAI API key (Saved to this session)"):
        with st.form("api_key_form"):
            st.text_input("Enter your OpenAI API key", type="password", key="openai_api_key_input")
            submit_key = st.form_submit_button("Save Key")

        if submit_key and st.session_state.openai_api_key_input:
            st.session_state.openai_api_key = st.session_state.openai_api_key_input
            st.success("API key saved to session.")

    if uploaded_image and st.session_state.get("openai_api_key"):
        # Prepare the image
        image_bytes = uploaded_image.read()
        mime_type, _ = mimetypes.guess_type(uploaded_image.name)
        base64_image = base64.b64encode(image_bytes).decode("utf-8")
        image_url = f"data:{mime_type};base64,{base64_image}"

        # Compose prompts
        system_prompt = (
            "You are an expert sourdough baking coach helping users troubleshoot their bread. "
            "They will submit a short message describing their issue and an image of their dough or loaf. "
            "Provide clear, concise, encouraging feedback based on what they share. "
            "Avoid jargon. Offer practical advice and likely causes of any issues."
        )
        user_message = f"Stage: {stage}\nIssue: {issue}\nPlease review the attached image."

        # Send to OpenAI
        openai.api_key = st.session_state["openai_api_key"]
        with st.spinner("Thinking like a sourdough expert..."):
            try:
                response = openai.chat.completions.create(
                    model="gpt-4-turbo",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": user_message},
                                {"type": "image_url", "image_url": {"url": image_url}}
                            ]
                        }
                    ],
                    max_tokens=1000
                )
                result = response.choices[0].message.content
                st.success("Here's what your sourdough expert says:")
                st.markdown(result)

            except Exception as e:
                st.error(f"Something went wrong: {e}")
    elif not st.session_state.get("openai_api_key"):
        st.warning("Please enter your OpenAI API key above.")
    elif not uploaded_image:
        st.info("Upload an image above to get started.")
    if st.button("🔄 Start Over (clear form + image)"):
        for key in ["selected_stage", "selected_issue", "uploaded_image"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

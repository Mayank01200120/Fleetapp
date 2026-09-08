import os
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Mahima Group Fleet Management & Dispatch Portal", layout="wide"
)


# Detect logo file in folder
logo_file = None
for ext in ["logo.png", "logo.jpg", "logo.jpeg", "logo.webp"]:
    if os.path.exists(ext):
        logo_file = ext
        break

# Display logo at the VERY TOP of the left sidebar
if logo_file:
    st.sidebar.image(logo_file, use_container_width=True)


# Admin Credentials
ADMIN_PASSWORD = "admin123"

# File paths
BOOKINGS_FILE = "fleet_bookings.xlsx"
FLEET_FILE = "fleet_cars.xlsx"
DRIVERS_FILE = "fleet_drivers.xlsx"
REQUESTERS_FILE = "fleet_requesters.xlsx"


def load_data(file_path, default_cols):
    if os.path.exists(file_path):
        return (
            pd.read_excel(file_path)
            if file_path.endswith(".xlsx")
            else pd.read_csv(file_path)
        )
    return pd.DataFrame(columns=default_cols)


def save_data(df, file_path):
    df.to_excel(file_path, index=False)


# Initialize Session States
if "bookings_df" not in st.session_state:
    st.session_state.bookings_df = load_data(
        BOOKINGS_FILE,
        [
            "ID",
            "Requester",
            "Property",
            "Vehicle Type Needed",
            "Date",
            "Assigned Car",
            "Assigned Driver",
            "Status",
        ],
    )

if "cars_df" not in st.session_state:
    st.session_state.cars_df = load_data(
        FLEET_FILE,
        ["Car ID", "Model", "Plate Number", "Category", "Availability"],
    )

if "drivers_df" not in st.session_state:
    st.session_state.drivers_df = load_data(
        DRIVERS_FILE,
        ["Driver ID", "Name", "Phone", "License No", "Status"],
    )

if "requesters_df" not in st.session_state:
    st.session_state.requesters_df = load_data(
        REQUESTERS_FILE,
        ["Requester ID", "Name", "Department", "Phone"],
    )

# --- SIDEBAR ACCESS CONTROL ---
st.sidebar.title("🔐 Portal Access")
role = st.sidebar.radio("Select Role", ["User / Agent", "Admin"])

is_admin_authenticated = False
if role == "Admin":
    password = st.sidebar.text_input("Enter Admin Password", type="password")
    if password == ADMIN_PASSWORD:
        is_admin_authenticated = True
        st.sidebar.success("Admin Authenticated")
    else:
        if password:
            st.sidebar.error("Incorrect Password")

st.title("🚗 Mahima Group Fleet Management")

# Define Navigation Tabs
if role == "Admin" and is_admin_authenticated:
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        [
            "⚙️ Dispatch & Approvals",
            "🚘 Car Fleet & Availability",
            "👨‍✈️ Drivers Directory",
            "👤 Requesters Directory",
            "📝 Submit Request",
        ]
    )
else:
    tab1, tab2 = st.tabs(["📝 Submit Request & View Availability", "📋 Track My Requests"])

# --- PUBLIC USER / AGENT TABS ---
if role != "Admin" or not is_admin_authenticated:
    with tab1:
        st.header("🚘 Live Car Fleet Availability")

        # Display availability summary metrics
        if not st.session_state.cars_df.empty:
            total_cars = len(st.session_state.cars_df)
            available_cnt = len(
                st.session_state.cars_df[
                    st.session_state.cars_df["Availability"] == "Available"
                ]
            )
            busy_cnt = len(
                st.session_state.cars_df[
                    st.session_state.cars_df["Availability"] == "Busy"
                ]
            )
            maint_cnt = len(
                st.session_state.cars_df[
                    st.session_state.cars_df["Availability"] == "Under Maintenance"
                ]
            )

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Fleet Cars", total_cars)
            col2.metric("🟢 Available", available_cnt)
            col3.metric("🔴 Busy", busy_cnt)
            col4.metric("🛠️ In Maintenance", maint_cnt)

            st.subheader("Current Fleet Status Directory")
            st.dataframe(
                st.session_state.cars_df[
                    ["Model", "Plate Number", "Category", "Availability"]
                ],
                use_container_width=True,
            )
        else:
            st.info("No cars listed in the directory yet. Admin can add vehicles in the Admin Panel.")

        st.markdown("---")
        st.header("Submit Booking Request")

        requester_names = (
            st.session_state.requesters_df["Name"].tolist()
            if not st.session_state.requesters_df.empty
            else []
        )

        with st.form(key="public_booking_form", clear_on_submit=True):
            if requester_names:
                requester = st.selectbox("Select Your Name", requester_names)
            else:
                requester = st.text_input("Requester Name")

            property_address = st.text_input("Property Address / Site Location")
            
            # Categories based on available fleet categories
            categories = (
                st.session_state.cars_df["Category"].unique().tolist()
                if not st.session_state.cars_df.empty
                else ["Sedan (Leasing)", "SUV (Site Inspection)", "Van (Maintenance)"]
            )
            vehicle_type = st.selectbox("Vehicle Category Needed", categories)
            booking_date = st.date_input("Booking Date")

            if st.form_submit_button("Submit Booking Request"):
                if requester and property_address:
                    new_id = len(st.session_state.bookings_df) + 101
                    new_entry = pd.DataFrame(
                        [
                            {
                                "ID": f"REQ-{new_id}",
                                "Requester": requester,
                                "Property": property_address,
                                "Vehicle Type Needed": vehicle_type,
                                "Date": str(booking_date),
                                "Assigned Car": "Unassigned",
                                "Assigned Driver": "Unassigned",
                                "Status": "Pending",
                            }
                        ]
                    )
                    st.session_state.bookings_df = pd.concat(
                        [st.session_state.bookings_df, new_entry],
                        ignore_index=True,
                    )
                    save_data(st.session_state.bookings_df, BOOKINGS_FILE)
                    st.success(
                        f"Request REQ-{new_id} submitted! Awaiting Admin Approval."
                    )
                else:
                    st.error("Please fill out all required fields.")

    with tab2:
        st.header("📋 Track All Submitted Requests")
        st.dataframe(st.session_state.bookings_df, use_container_width=True)

# --- PROTECTED ADMIN TABS ---
else:
    # ADMIN TAB 1: DISPATCH & STATUS MANAGEMENT
    with tab1:
        st.header("⚙️ Dispatch & Assignment Control")

        available_cars = ["Unassigned"]
        if not st.session_state.cars_df.empty:
            avail_df = st.session_state.cars_df[
                st.session_state.cars_df["Availability"] == "Available"
            ]
            available_cars += avail_df["Model"].tolist()

        driver_options = ["Unassigned"] + (
            st.session_state.drivers_df["Name"].tolist()
            if not st.session_state.drivers_df.empty
            else []
        )

        st.subheader("Manage Bookings & Assign Resources")
        edited_bookings = st.data_editor(
            st.session_state.bookings_df,
            column_config={
                "Status": st.column_config.SelectboxColumn(
                    "Status",
                    options=["Pending", "Approved", "Rejected", "Completed"],
                    required=True,
                ),
                "Assigned Car": st.column_config.SelectboxColumn(
                    "Assigned Car", options=available_cars, required=True
                ),
                "Assigned Driver": st.column_config.SelectboxColumn(
                    "Assigned Driver", options=driver_options, required=True
                ),
            },
            key="admin_editor",
            use_container_width=True,
        )

        if st.button("💾 Save & Sync Fleet Availability"):
            st.session_state.bookings_df = edited_bookings
            save_data(edited_bookings, BOOKINGS_FILE)

            if not st.session_state.cars_df.empty:
                busy_cars = edited_bookings[
                    (edited_bookings["Status"] == "Approved")
                    & (edited_bookings["Assigned Car"] != "Unassigned")
                ]["Assigned Car"].tolist()

                for idx, row in st.session_state.cars_df.iterrows():
                    # Don't override 'Under Maintenance' vehicles to Available automatically
                    if row["Availability"] != "Under Maintenance":
                        if row["Model"] in busy_cars:
                            st.session_state.cars_df.at[idx, "Availability"] = "Busy"
                        else:
                            st.session_state.cars_df.at[idx, "Availability"] = "Available"

                save_data(st.session_state.cars_df, FLEET_FILE)

            st.success("Assignments updated & Car availability refreshed!")

    # ADMIN TAB 2: CARS FLEET & AVAILABILITY
    with tab2:
        st.header("🚘 Fleet Cars Directory & Availability Status")

        edited_cars = st.data_editor(
            st.session_state.cars_df,
            column_config={
                "Availability": st.column_config.SelectboxColumn(
                    "Availability",
                    options=["Available", "Busy", "Under Maintenance"],
                    required=True,
                )
            },
            num_rows="dynamic",
            key="cars_editor",
            use_container_width=True,
        )

        if st.button("💾 Save Fleet Directory"):
            st.session_state.cars_df = edited_cars
            save_data(edited_cars, FLEET_FILE)
            st.success("Car fleet updated successfully!")

    # ADMIN TAB 3: DRIVERS DIRECTORY
    with tab3:
        st.header("👨‍✈️ Drivers Directory")
        edited_drivers = st.data_editor(
            st.session_state.drivers_df,
            num_rows="dynamic",
            key="drivers_editor",
            use_container_width=True,
        )
        if st.button("💾 Save Drivers"):
            st.session_state.drivers_df = edited_drivers
            save_data(edited_drivers, DRIVERS_FILE)
            st.success("Driver records updated!")

    # ADMIN TAB 4: REQUESTERS DIRECTORY
    with tab4:
        st.header("👤 Requesters Directory")
        edited_reqs = st.data_editor(
            st.session_state.requesters_df,
            num_rows="dynamic",
            key="requesters_editor",
            use_container_width=True,
        )
        if st.button("💾 Save Requesters"):
            st.session_state.requesters_df = edited_reqs
            save_data(edited_reqs, REQUESTERS_FILE)
            st.success("Requester records updated!")

    # ADMIN TAB 5: SUBMIT REQUEST (ADMIN VIEW)
    with tab5:
        st.header("Create Request as Admin")
        st.info("Use Tab 1 (Dispatch & Approvals) to process incoming requests.")
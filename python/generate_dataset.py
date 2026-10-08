import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta


# =========================================================
# 0. CONFIGURATION
# =========================================================

np.random.seed(42)
random.seed(42)

N_USERS = 20_000
EXTRA_VISITORS = 12_000

START_DATE = datetime(2025, 1, 1)
END_DATE = datetime(2025, 12, 31)

countries = [
    "United States",
    "United Kingdom",
    "Germany",
    "France",
    "Spain",
    "Netherlands",
    "Canada",
    "Australia"
]

devices = [
    "Desktop",
    "Mobile",
    "Tablet"
]

channels = [
    "Organic Search",
    "Paid Search",
    "Facebook Ads",
    "Referral",
    "Direct",
    "Email Campaign"
]

plans = [
    "Free",
    "Pro",
    "Family"
]


# =========================================================
# 1. WEIGHTS
# =========================================================

country_weights = [
    0.24,  # USA
    0.15,  # UK
    0.14,  # Germany
    0.11,  # France
    0.10,  # Spain
    0.07,  # Netherlands
    0.11,  # Canada
    0.08   # Australia
]

device_weights = [
    0.46,  # Desktop
    0.38,  # Mobile
    0.16   # Tablet
]

channel_weights = [
    0.16,  # Organic Search
    0.13,  # Paid Search
    0.08,  # Facebook Ads
    0.12,  # Referral
    0.11,  # Direct
    0.40   # Email Campaign
]

plan_weights = [
    0.62,  # Free
    0.26,  # Pro
    0.12   # Family
]


# =========================================================
# 2. FUNNEL BASE PROBABILITIES
# =========================================================

P_EMAIL_VERIFIED = 0.78
P_TRIAL_STARTED = 0.70
P_ONBOARDING_COMPLETED = 0.83
P_FIRST_KEY_ACTION = 0.79
P_SUBSCRIPTION_STARTED = 0.54


# =========================================================
# 3. SEGMENT ADJUSTMENTS
# =========================================================

channel_adjustments = {
    "Email Campaign": 1.20,
    "Referral": 1.12,
    "Organic Search": 1.05,
    "Direct": 0.98,
    "Paid Search": 0.92,
    "Facebook Ads": 0.82
}

device_adjustments = {
    "Desktop": 1.08,
    "Mobile": 0.97,
    "Tablet": 0.90
}

country_adjustments = {
    "United States": 1.10,
    "United Kingdom": 1.06,
    "Germany": 1.03,
    "France": 0.98,
    "Spain": 0.95,
    "Netherlands": 1.01,
    "Canada": 1.05,
    "Australia": 1.04
}


# =========================================================
# 3B. PRODUCT USAGE (LOGIN / FEATURE USED) PARAMETERS
# =========================================================

# Share of activated users who become "loyal" (long-tail engagement,
# activity continues almost until END_DATE instead of stopping early).
P_LOYAL_USER = 0.25

# Exponential mean gap (in days) between consecutive Login events.
# Loyal users log in slightly more often on average, but the key
# difference is HOW LONG their activity window lasts, not the gap itself.
LOGIN_GAP_LOYAL = (3, 7)      # uniform range to sample mean gap from
LOGIN_GAP_TYPICAL = (4, 10)

# How long (in days from activation) a "typical" user keeps being active
# before churning out of the product entirely. Loyal users instead keep
# going until END_DATE.
TYPICAL_ACTIVITY_WINDOW = (20, 90)

# Feature Used events piggyback on the same engagement window, but are
# somewhat sparser than logins.
FEATURE_GAP_MULTIPLIER = 1.6


# =========================================================
# 4. HELPER FUNCTIONS
# =========================================================

def weighted_choice(options, weights):
    return np.random.choice(options, p=weights)


def clamp(value, low=0.01, high=0.99):
    return max(low, min(high, value))


def random_datetime(start, end):
    delta = end - start

    random_seconds = random.randint(
        0,
        int(delta.total_seconds())
    )

    return start + timedelta(
        seconds=random_seconds
    )


def generate_decaying_event_times(anchor_time, mean_gap_days, max_days, end_date):
    """
    Generate a list of datetimes representing recurring engagement
    (logins or feature usage), spaced by exponential gaps.

    Exponential inter-arrival times naturally produce a realistic
    engagement pattern: lots of activity early on, tapering off later,
    instead of activity spread uniformly across a fixed window.

    - anchor_time: starting point (roughly, when the user activated)
    - mean_gap_days: average number of days between consecutive events
    - max_days: how many days from anchor_time this user stays active at all
    - end_date: hard cutoff, activity never goes past the observation window
    """

    times = []
    t = 0.0

    while True:
        gap = np.random.exponential(scale=mean_gap_days)
        t += gap

        if t > max_days:
            break

        event_time = anchor_time + timedelta(
            days=t,
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59)
        )

        if event_time > end_date:
            break

        times.append(event_time)

    return times


# =========================================================
# 5. USERS TABLE
# =========================================================

users = []

for i in range(N_USERS):

    signup = random_datetime(
        START_DATE,
        END_DATE
    )

    country = weighted_choice(
        countries,
        country_weights
    )

    device = weighted_choice(
        devices,
        device_weights
    )

    channel = weighted_choice(
        channels,
        channel_weights
    )

    plan_interest = weighted_choice(
        plans,
        plan_weights
    )

    users.append({
        "user_id": f"U{i + 1:06}",

        "signup_date":
            signup.strftime("%Y-%m-%d"),

        "country":
            country,

        "device_type":
            device,

        "acquisition_channel":
            channel,

        "plan_interest":
            plan_interest
    })


users_df = pd.DataFrame(users)


# =========================================================
# 6. EVENTS TABLE
# =========================================================

events = []

event_id = 1


# =========================================================
# 6A. VISITS FROM USERS WHO SIGNED UP
# =========================================================

for _, user in users_df.iterrows():

    uid = user["user_id"]

    signup = datetime.strptime(
        user["signup_date"],
        "%Y-%m-%d"
    )

    visit_time = (
        signup
        - timedelta(
            days=random.randint(0, 7),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59)
        )
    )

    events.append({
        "event_id": f"E{event_id:08}",
        "user_id": uid,
        "event_datetime":
            visit_time.strftime("%Y-%m-%d %H:%M:%S"),
        "event_type": "Visit"
    })

    event_id += 1


# =========================================================
# 6B. VISITORS WHO NEVER SIGN UP
# =========================================================

for i in range(EXTRA_VISITORS):

    visitor_id = f"V{i + 1:06}"

    visit_time = random_datetime(
        START_DATE,
        END_DATE
    )

    events.append({
        "event_id": f"E{event_id:08}",
        "user_id": visitor_id,
        "event_datetime":
            visit_time.strftime("%Y-%m-%d %H:%M:%S"),
        "event_type": "Visit"
    })

    event_id += 1


# =========================================================
# 6C. FUNNEL EVENTS + PRODUCT USAGE
# =========================================================

for _, user in users_df.iterrows():

    uid = user["user_id"]

    signup = datetime.strptime(
        user["signup_date"],
        "%Y-%m-%d"
    )

    country = user["country"]
    device = user["device_type"]
    channel = user["acquisition_channel"]

    # -----------------------------------------
    # Segment multiplier
    # -----------------------------------------

    multiplier = (
        channel_adjustments[channel]
        * device_adjustments[device]
        * country_adjustments[country]
    )

    p_email = clamp(
        P_EMAIL_VERIFIED * multiplier
    )

    p_trial = clamp(
        P_TRIAL_STARTED * multiplier
    )

    p_onboarding = clamp(
        P_ONBOARDING_COMPLETED * multiplier
    )

    p_key_action = clamp(
        P_FIRST_KEY_ACTION * multiplier
    )

    p_subscription = clamp(
        P_SUBSCRIPTION_STARTED * multiplier
    )


    # -----------------------------------------
    # SIGN UP
    # -----------------------------------------

    current_time = (
        signup
        + timedelta(
            hours=random.randint(1, 12)
        )
    )

    events.append({
        "event_id": f"E{event_id:08}",
        "user_id": uid,
        "event_datetime":
            current_time.strftime("%Y-%m-%d %H:%M:%S"),
        "event_type": "Sign Up"
    })

    event_id += 1


    # -----------------------------------------
    # EMAIL VERIFIED
    # -----------------------------------------

    if random.random() > p_email:
        continue

    current_time += timedelta(
        hours=random.randint(2, 48)
    )

    events.append({
        "event_id": f"E{event_id:08}",
        "user_id": uid,
        "event_datetime":
            current_time.strftime("%Y-%m-%d %H:%M:%S"),
        "event_type": "Email Verified"
    })

    event_id += 1


    # -----------------------------------------
    # TRIAL STARTED
    # -----------------------------------------

    if random.random() > p_trial:
        continue

    current_time += timedelta(
        hours=random.randint(4, 72)
    )

    events.append({
        "event_id": f"E{event_id:08}",
        "user_id": uid,
        "event_datetime":
            current_time.strftime("%Y-%m-%d %H:%M:%S"),
        "event_type": "Trial Started"
    })

    event_id += 1


    # -----------------------------------------
    # ONBOARDING COMPLETED
    # -----------------------------------------

    if random.random() > p_onboarding:
        continue

    current_time += timedelta(
        hours=random.randint(2, 60)
    )

    events.append({
        "event_id": f"E{event_id:08}",
        "user_id": uid,
        "event_datetime":
            current_time.strftime("%Y-%m-%d %H:%M:%S"),
        "event_type": "Onboarding Completed"
    })

    event_id += 1


    # -----------------------------------------
    # FIRST KEY ACTION
    # -----------------------------------------

    if random.random() > p_key_action:
        continue

    current_time += timedelta(
        hours=random.randint(6, 120)
    )

    events.append({
        "event_id": f"E{event_id:08}",
        "user_id": uid,
        "event_datetime":
            current_time.strftime("%Y-%m-%d %H:%M:%S"),
        "event_type": "First Key Action"
    })

    event_id += 1


    # -----------------------------------------
    # SUBSCRIPTION STARTED
    # -----------------------------------------

    if random.random() <= p_subscription:

        current_time += timedelta(
            days=random.randint(1, 30),
            hours=random.randint(1, 12)
        )

        events.append({
            "event_id": f"E{event_id:08}",
            "user_id": uid,
            "event_datetime":
                current_time.strftime("%Y-%m-%d %H:%M:%S"),
            "event_type": "Subscription Started"
        })

        event_id += 1


    # =====================================================
    # PRODUCT USAGE (LOGIN / FEATURE USED)
    # =====================================================
    #
    # Activated users (reached First Key Action) generate ongoing
    # Login / Feature Used events. Instead of scattering them
    # uniformly across a fixed 90-day window (which produces an
    # unrealistic *rising* retention curve), engagement is modeled
    # as a decaying process:
    #
    #   - a minority of users ("loyal") keep coming back for
    #     most of the remaining observation period
    #   - the majority ("typical") taper off within a few weeks
    #     to a few months, at a per-user random pace
    #
    # This produces a monotonically decreasing retention curve,
    # consistent with what's typically observed in real products.

    is_loyal = random.random() < P_LOYAL_USER

    if is_loyal:
        login_mean_gap = random.uniform(*LOGIN_GAP_LOYAL)
        activity_window_days = (END_DATE - current_time).days
    else:
        login_mean_gap = random.uniform(*LOGIN_GAP_TYPICAL)
        activity_window_days = random.randint(*TYPICAL_ACTIVITY_WINDOW)

    activity_window_days = max(activity_window_days, 1)

    login_times = generate_decaying_event_times(
        anchor_time=current_time,
        mean_gap_days=login_mean_gap,
        max_days=activity_window_days,
        end_date=END_DATE
    )

    for login_time in login_times:

        events.append({
            "event_id": f"E{event_id:08}",
            "user_id": uid,
            "event_datetime":
                login_time.strftime("%Y-%m-%d %H:%M:%S"),
            "event_type": "Login"
        })

        event_id += 1

    feature_times = generate_decaying_event_times(
        anchor_time=current_time,
        mean_gap_days=login_mean_gap * FEATURE_GAP_MULTIPLIER,
        max_days=activity_window_days,
        end_date=END_DATE
    )

    for feature_time in feature_times:

        events.append({
            "event_id": f"E{event_id:08}",
            "user_id": uid,
            "event_datetime":
                feature_time.strftime("%Y-%m-%d %H:%M:%S"),
            "event_type": "Feature Used"
        })

        event_id += 1


# =========================================================
# 7. CREATE EVENTS DATAFRAME
# =========================================================

events_df = pd.DataFrame(events)

events_df["event_datetime"] = pd.to_datetime(
    events_df["event_datetime"]
)

events_df = events_df.sort_values(
    ["user_id", "event_datetime"]
).reset_index(drop=True)

events_df["event_id"] = [
    f"E{i + 1:08}"
    for i in range(len(events_df))
]


# =========================================================
# 8. SUBSCRIPTIONS TABLE
# =========================================================

subscriptions = []

subscription_id = 1


subscription_events = (
    events_df[
        events_df["event_type"]
        == "Subscription Started"
    ]
    .sort_values("event_datetime")
    .drop_duplicates("user_id")
)


users_lookup = (
    users_df
    .set_index("user_id")
)


for _, event in subscription_events.iterrows():

    uid = event["user_id"]

    subscription_date = event[
        "event_datetime"
    ]

    plan_interest = users_lookup.loc[
        uid,
        "plan_interest"
    ]


    # -----------------------------------------
    # PLAN
    # -----------------------------------------

    if plan_interest == "Family":

        plan_tier = np.random.choice(
            ["Family", "Pro"],
            p=[0.75, 0.25]
        )

    elif plan_interest == "Pro":

        plan_tier = np.random.choice(
            ["Pro", "Family"],
            p=[0.85, 0.15]
        )

    else:

        plan_tier = np.random.choice(
            ["Pro", "Family"],
            p=[0.70, 0.30]
        )


    # -----------------------------------------
    # BILLING
    # -----------------------------------------

    billing_cycle = np.random.choice(
        ["Monthly", "Annual"],
        p=[0.72, 0.28]
    )


    # -----------------------------------------
    # PRICE
    # -----------------------------------------

    if plan_tier == "Pro":

        monthly_revenue = np.random.choice(
            [12.99, 14.99, 19.99],
            p=[0.25, 0.45, 0.30]
        )

    else:

        monthly_revenue = np.random.choice(
            [19.99, 24.99, 29.99],
            p=[0.25, 0.40, 0.35]
        )


    # -----------------------------------------
    # CHURN
    # -----------------------------------------

    # 25% churn within the observation period

    if random.random() < 0.25:

        churn_days = random.randint(
            30,
            180
        )

        end_date = (
            subscription_date
            + timedelta(
                days=churn_days
            )
        )

        if end_date > END_DATE:
            end_date = pd.NaT

    else:

        end_date = pd.NaT


    subscriptions.append({

        "subscription_id":
            f"S{subscription_id:06}",

        "user_id":
            uid,

        "subscription_start_date":
            subscription_date.strftime(
                "%Y-%m-%d"
            ),

        "plan_tier":
            plan_tier,

        "monthly_revenue":
            monthly_revenue,

        "billing_cycle":
            billing_cycle,

        "end_date":
            end_date.strftime("%Y-%m-%d")
            if pd.notna(end_date)
            else None
    })

    subscription_id += 1


subscriptions_df = pd.DataFrame(
    subscriptions
)


# =========================================================
# 9. SAVE CSV FILES
# =========================================================

users_df.to_csv(
    "saas_users.csv",
    index=False
)

events_df.to_csv(
    "saas_events.csv",
    index=False
)

subscriptions_df.to_csv(
    "saas_subscriptions.csv",
    index=False
)


# =========================================================
# 10. DATA QUALITY CHECKS
# =========================================================

print("=" * 60)
print("SAAS PRODUCT ANALYTICS DATASET")
print("=" * 60)

print(
    f"\nUsers: {len(users_df):,}"
)

print(
    f"Events: {len(events_df):,}"
)

print(
    f"Subscriptions: {len(subscriptions_df):,}"
)


print("\n" + "-" * 60)
print("EVENT DISTRIBUTION")
print("-" * 60)

print(
    events_df["event_type"]
    .value_counts()
)


print("\n" + "-" * 60)
print("USERS BY ACQUISITION CHANNEL")
print("-" * 60)

print(
    users_df["acquisition_channel"]
    .value_counts()
)


print("\n" + "-" * 60)
print("SUBSCRIPTION PLANS")
print("-" * 60)

if len(subscriptions_df) > 0:

    print(
        subscriptions_df[
            "plan_tier"
        ].value_counts()
    )

else:

    print("No subscriptions generated.")


print("\n" + "-" * 60)
print("FILES CREATED")
print("-" * 60)

print("saas_users.csv")
print("saas_events.csv")
print("saas_subscriptions.csv")

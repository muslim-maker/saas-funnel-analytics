-- ============================================================
-- SaaS Product Analytics: Funnel, Cohort Retention, LTV/Churn
-- Dialect: ClickHouse (chdb)
-- Tables: saas_users, saas_events, saas_subscriptions
-- ============================================================
 
 
-- ============================================================
-- BLOCK 1: FUNNEL ANALYSIS
-- ============================================================

-- 1.1 Base funnel: unique users reaching each stage

select
    'Visit' as funnel_step,
    count(distinct case when event_type = 'Visit' then user_id end) as user_count
from saas_events
 
union all
 
select
    'Sign Up',
    count(distinct case when event_type = 'Sign Up' then user_id end)
from saas_events
 
union all
 
select
    'Email Verified',
    count(distinct case when event_type = 'Email Verified' then user_id end)
from saas_events
 
union all
 
select
    'Trial Started',
    count(distinct case when event_type = 'Trial Started' then user_id end)
from saas_events
 
union all
 
select
    'Onboarding Completed',
    count(distinct case when event_type = 'Onboarding Completed' then user_id end)
from saas_events
 
union all
 
select
    'First Key Action',
    count(distinct case when event_type = 'First Key Action' then user_id end)
from saas_events
 
union all
 
select
    'Subscription Started',
    count(distinct case when event_type = 'Subscription Started' then user_id end)
from saas_events;

-- 1.2 Conversion to subscription by acquisition channel
select
    u.acquisition_channel,
    count(distinct u.user_id) as total_users,
    count(distinct s.user_id) as subscribers,
    round(
        count(distinct s.user_id) * 100.0 / count(distinct u.user_id),
        2
    ) as conversion_to_subscription_pct
from saas_users u
left join saas_subscriptions s
    on u.user_id = s.user_id
group by u.acquisition_channel
order by conversion_to_subscription_pct desc;
 
 
-- 1.3 Conversion to subscription by country
select
    u.country,
    count(distinct u.user_id) as total_users,
    count(distinct s.user_id) as subscribers,
    round(
        count(distinct s.user_id) * 100.0 / count(distinct u.user_id),
        2
    ) as conversion_to_subscription_pct
from saas_users u
left join saas_subscriptions s
    on u.user_id = s.user_id
group by u.country
order by conversion_to_subscription_pct desc, total_users desc;
 
 
-- 1.4 Conversion to subscription by device type
select
    u.device_type,
    count(distinct u.user_id) as total_users,
    count(distinct s.user_id) as subscribers,
    round(
        count(distinct s.user_id) * 100.0 / count(distinct u.user_id),
        2
    ) as conversion_to_subscription_pct
from saas_users u
left join saas_subscriptions s
    on u.user_id = s.user_id
group by u.device_type
order by conversion_to_subscription_pct desc;

-- 1.5 Full funnel with step-level conversion rates, by acquisition channel
with acquisition as (
    select
        acquisition_channel,
        count(distinct case when event_type = 'Sign Up' then user_id end) as sign_up,
        count(distinct case when event_type = 'Email Verified' then user_id end) as email_verified,
        count(distinct case when event_type = 'Trial Started' then user_id end) as trials,
        count(distinct case when event_type = 'Onboarding Completed' then user_id end) as onboarding_completed,
        count(distinct case when event_type = 'First Key Action' then user_id end) as activated,
        count(distinct case when event_type = 'Subscription Started' then user_id end) as paid_users
    from saas_events
    join saas_users using (user_id)
    group by acquisition_channel
)
 
select
    acquisition_channel,
    sign_up,
    email_verified,
    round(email_verified * 100 / sign_up, 2) as signup_to_verified_rate,
    trials,
    round(trials * 100 / email_verified, 2) as verified_to_trial_rate,
    onboarding_completed,
    round(onboarding_completed * 100 / trials, 2) as trial_to_onboarding_rate,
    activated,
    round(activated * 100 / onboarding_completed, 2) as onboarding_to_activated_rate,
    paid_users,
    round(paid_users * 100 / activated, 2) as activated_to_paid_rate,
    round(paid_users * 100 / sign_up, 2) as overall_signup_to_paid_rate
from acquisition
order by overall_signup_to_paid_rate desc;
-- 2.1 Retention matrix by signup cohort, 30-day windows

with cohort_sizes as (
    select
        toStartOfMonth(signup_date) as cohort_month,
        count(distinct user_id) as cohort_size
    from saas_users
    group by cohort_month
),
 
user_activity as (
    select
        u.user_id,
        toStartOfMonth(u.signup_date) as cohort_month,
        intDiv(dateDiff('day', u.signup_date, toDate(e.event_datetime)), 30) as period_number
    from saas_users u
    join saas_events e
        on u.user_id = e.user_id
    where e.event_type = 'Login'
    group by u.user_id, cohort_month, period_number
)
 
select
    c.cohort_month,
    a.period_number,
    count(distinct a.user_id) as active_users,
    c.cohort_size,
    round(count(distinct a.user_id) * 100.0 / c.cohort_size, 2) as retention_rate
from cohort_sizes c
left join user_activity a
    on c.cohort_month = a.cohort_month
where a.period_number >= 0
group by c.cohort_month, a.period_number, c.cohort_size
order by c.cohort_month, a.period_number;
 
 
-- 2.2 Retention trend across cohorts (period 1 rate, month over month)

with cohort_sizes as (
    select
        toStartOfMonth(signup_date) as cohort_month,
        count(distinct user_id) as cohort_size
    from saas_users
    group by cohort_month
),
 
user_activity as (
    select
        u.user_id,
        toStartOfMonth(u.signup_date) as cohort_month,
        intDiv(dateDiff('day', u.signup_date, toDate(e.event_datetime)), 30) as period_number
    from saas_users u
    join saas_events e
        on u.user_id = e.user_id
    where e.event_type = 'Login'
    group by u.user_id, cohort_month, period_number
)
 
select
    c.cohort_month,
    round(count(distinct a.user_id) * 100.0 / c.cohort_size, 2) as period_1_retention_rate
from cohort_sizes c
left join user_activity a
    on c.cohort_month = a.cohort_month
where a.period_number = 1
group by c.cohort_month, c.cohort_size
order by c.cohort_month;
 
 
-- 2.3 Retention by acquisition channel, 30-day windows
with cohort_sizes as (
    select
        acquisition_channel,
        count(distinct user_id) as cohort_size
    from saas_users
    group by acquisition_channel
),
 
user_activity as (
    select
        u.user_id,
        u.acquisition_channel,
        intDiv(dateDiff('day', u.signup_date, toDate(e.event_datetime)), 30) as period_number
    from saas_users u
    join saas_events e
        on u.user_id = e.user_id
    where e.event_type = 'Login'
    group by u.user_id, u.acquisition_channel, period_number
)
 
select
    c.acquisition_channel,
    a.period_number,
    round(count(distinct a.user_id) * 100.0 / c.cohort_size, 2) as retention_rate
from cohort_sizes c
left join user_activity a
    on c.acquisition_channel = a.acquisition_channel
where a.period_number between 0 and 8
group by c.acquisition_channel, a.period_number, c.cohort_size
order by c.acquisition_channel, a.period_number;
-- ============================================================
-- BLOCK 3: LTV / CHURN ANALYSIS
-- ============================================================
 
-- 3.1 Overall churn rate
select
    count(distinct user_id) as total_subscribers,
    count(distinct case whenend_date != '1970-01-01' then user_id end) as churned_users,
    round(
        count(distinct case when end_date != '1970-01-01' then user_id end) * 100.0 / count(distinct user_id),
        2
    ) as churn_rate_pct
from saas_subscriptions;
 
 
-- 3.2 Churn rate by plan_tier and billing_cycle
select
    plan_tier,
    billing_cycle,
    count(distinct user_id) as total_subscribers,
    count(distinct case when end_date != '1970-01-01' then user_id end) as churned_users,
    round(
        count(distinct case when end_date != '1970-01-01' then user_id end) * 100.0 / count(distinct user_id),
        2
    ) as churn_rate_pct
from saas_subscriptions
group by plan_tier, billing_cycle
order by churn_rate_pct desc;
 
-- 3.3 Average LTV by acquisition channel
with lifetime as (
    select
        s.user_id,
        u.acquisition_channel,
        s.monthly_revenue,
        case
            when s.end_date != '1970-01-01'
                then dateDiff('day', toDate(s.subscription_start_date), toDate(s.end_date))
            else dateDiff('day', toDate(s.subscription_start_date), toDate('2025-12-31'))
        end as lifetime_days
    from saas_subscriptions s
    join saas_users u using (user_id)
)
 
select
    acquisition_channel,
    count(distinct user_id) as subscribers,
    round(avg(lifetime_days / 30.0), 2) as avg_lifetime_months,
    round(avg(monthly_revenue * (lifetime_days / 30.0)), 2) as avg_ltv
from lifetime
group by acquisition_channel
order by avg_ltv desc;
 
 
-- 3.4 LTV vs churn rate by segment 
with lifetime as (
    select
        s.user_id,
        u.acquisition_channel,
        s.plan_tier,
        s.monthly_revenue,
        case when s.end_date != '1970-01-01' then 1 else 0 end as is_churned,
        case
            when s.end_date != '1970-01-01' 
                then dateDiff('day', toDate(s.subscription_start_date), toDate(s.end_date))
            else dateDiff('day', toDate(s.subscription_start_date), toDate('2025-12-31'))
        end as lifetime_days
    from saas_subscriptions s
    join saas_users u using (user_id)
)
 
select
    acquisition_channel,
    plan_tier,
    count(distinct user_id) as subscribers,
    round(avg(monthly_revenue * (lifetime_days / 30.0)), 2) as avg_ltv,
    round(avg(is_churned) * 100, 2) as churn_rate_pct
from lifetime
group by acquisition_channel, plan_tier
order by avg_ltv desc;
 
 


-- ==================================================
-- GOPARKIN EV DASHBOARD PERFORMANCE INDEXES
-- ==================================================

-- Transaction reporting date
CREATE INDEX CONCURRENTLY IF NOT EXISTS
    idx_ev_paid_datetime_paid_dt
ON public.ev_paid_datetime (paid_dt_p8);

-- Car park relationship
CREATE INDEX CONCURRENTLY IF NOT EXISTS
    idx_ev_paid_datetime_car_park
ON public.ev_paid_datetime (car_park_id);

-- Car park owner relationship
CREATE INDEX CONCURRENTLY IF NOT EXISTS
    idx_car_park_owner_id
ON public.car_park (car_park_owner_id);

-- Car park operator relationship
CREATE INDEX CONCURRENTLY IF NOT EXISTS
    idx_car_park_operator_id
ON public.car_park (car_park_operator_id);

-- Update database statistics
ANALYZE public.ev_paid_datetime;
ANALYZE public.car_park;
ANALYZE public.car_park_owner;
ANALYZE public.car_park_operator;

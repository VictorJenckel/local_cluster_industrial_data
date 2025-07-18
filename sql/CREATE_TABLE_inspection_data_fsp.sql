CREATE TABLE inspection_data_fsp (
    time timestamp NOT NULL,
    lite_id integer NOT NULL,
    cap_id integer,
    convoy_id integer,
    tolerance_nbr integer,
    nominal_length double precision,
    nominal_width double precision,
    length_diff double precision,
    width_diff double precision,
    diagonal double precision,
    rectangularity text,
    rotation double precision,
    position double precision,
    leading_corner_left text,
    leading_edge text,
    leading_corner_right text,
    right_edge text,
    trailing_corner_right text,
    trailing_edge text,
    trailing_corner_left text,
    left_edge text,
    markings text,
    total_result text,
    top_curv double precision,
    top_dev double precision,
    rgt_curv double precision,
    rgt_dev double precision,
    btm_curv double precision,
    btm_dev double precision,
    lft_curv double precision,
    lft_dev double precision,
    CONSTRAINT inspection_data_fsp_unique UNIQUE (time, lite_id)
    PARTITION BY RANGE (time)
);

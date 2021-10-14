--
-- PostgreSQL database dump
--

-- Dumped from database version 14.0 (Debian 14.0-1.pgdg110+1)
-- Dumped by pg_dump version 14.0

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: GlobalTag; Type: TABLE; Schema: public; Owner: login
--

CREATE TABLE public."GlobalTag" (
    id integer NOT NULL,
    name character varying(80) NOT NULL,
    description character varying(255) NOT NULL,
    created timestamp with time zone NOT NULL,
    updated timestamp with time zone NOT NULL,
    status_id bigint,
    type_id bigint
);


ALTER TABLE public."GlobalTag" OWNER TO login;

--
-- Name: GlobalTagStatus; Type: TABLE; Schema: public; Owner: login
--

CREATE TABLE public."GlobalTagStatus" (
    id bigint NOT NULL,
    name character varying(80) NOT NULL,
    description character varying(255) NOT NULL,
    created timestamp with time zone NOT NULL
);


ALTER TABLE public."GlobalTagStatus" OWNER TO login;

--
-- Name: GlobalTagType; Type: TABLE; Schema: public; Owner: login
--

CREATE TABLE public."GlobalTagType" (
    id bigint NOT NULL,
    name character varying(80) NOT NULL,
    description character varying(255) NOT NULL,
    created timestamp with time zone NOT NULL
);


ALTER TABLE public."GlobalTagType" OWNER TO login;

--
-- Name: GlobalTag_id_seq; Type: SEQUENCE; Schema: public; Owner: login
--

CREATE SEQUENCE public."GlobalTag_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public."GlobalTag_id_seq" OWNER TO login;

--
-- Name: GlobalTag_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: login
--

ALTER SEQUENCE public."GlobalTag_id_seq" OWNED BY public."GlobalTag".id;


--
-- Name: PayloadIOV; Type: TABLE; Schema: public; Owner: login
--

CREATE TABLE public."PayloadIOV" (
    id integer NOT NULL,
    payload_url character varying(255) NOT NULL,
    major_iov bigint NOT NULL,
    minor_iov bigint NOT NULL,
    description character varying(255) NOT NULL,
    created timestamp with time zone NOT NULL,
    updated timestamp with time zone NOT NULL,
    payload_list_id integer
);


ALTER TABLE public."PayloadIOV" OWNER TO login;

--
-- Name: PayloadIOV_id_seq; Type: SEQUENCE; Schema: public; Owner: login
--

CREATE SEQUENCE public."PayloadIOV_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public."PayloadIOV_id_seq" OWNER TO login;

--
-- Name: PayloadIOV_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: login
--

ALTER SEQUENCE public."PayloadIOV_id_seq" OWNED BY public."PayloadIOV".id;


--
-- Name: PayloadList; Type: TABLE; Schema: public; Owner: login
--

CREATE TABLE public."PayloadList" (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    description character varying(255) NOT NULL,
    created timestamp with time zone NOT NULL,
    updated timestamp with time zone NOT NULL,
    global_tag_id integer,
    payload_type_id bigint
);


ALTER TABLE public."PayloadList" OWNER TO login;

--
-- Name: PayloadList_id_seq; Type: SEQUENCE; Schema: public; Owner: login
--

CREATE SEQUENCE public."PayloadList_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public."PayloadList_id_seq" OWNER TO login;

--
-- Name: PayloadList_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: login
--

ALTER SEQUENCE public."PayloadList_id_seq" OWNED BY public."PayloadList".id;


--
-- Name: PayloadType; Type: TABLE; Schema: public; Owner: login
--

CREATE TABLE public."PayloadType" (
    id bigint NOT NULL,
    name character varying(80) NOT NULL,
    description character varying(255) NOT NULL,
    created timestamp with time zone NOT NULL
);


ALTER TABLE public."PayloadType" OWNER TO login;

--
-- Name: auth_group; Type: TABLE; Schema: public; Owner: login
--

CREATE TABLE public.auth_group (
    id integer NOT NULL,
    name character varying(150) NOT NULL
);


ALTER TABLE public.auth_group OWNER TO login;

--
-- Name: auth_group_id_seq; Type: SEQUENCE; Schema: public; Owner: login
--

CREATE SEQUENCE public.auth_group_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.auth_group_id_seq OWNER TO login;

--
-- Name: auth_group_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: login
--

ALTER SEQUENCE public.auth_group_id_seq OWNED BY public.auth_group.id;


--
-- Name: auth_group_permissions; Type: TABLE; Schema: public; Owner: login
--

CREATE TABLE public.auth_group_permissions (
    id integer NOT NULL,
    group_id integer NOT NULL,
    permission_id integer NOT NULL
);


ALTER TABLE public.auth_group_permissions OWNER TO login;

--
-- Name: auth_group_permissions_id_seq; Type: SEQUENCE; Schema: public; Owner: login
--

CREATE SEQUENCE public.auth_group_permissions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.auth_group_permissions_id_seq OWNER TO login;

--
-- Name: auth_group_permissions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: login
--

ALTER SEQUENCE public.auth_group_permissions_id_seq OWNED BY public.auth_group_permissions.id;


--
-- Name: auth_permission; Type: TABLE; Schema: public; Owner: login
--

CREATE TABLE public.auth_permission (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    content_type_id integer NOT NULL,
    codename character varying(100) NOT NULL
);


ALTER TABLE public.auth_permission OWNER TO login;

--
-- Name: auth_permission_id_seq; Type: SEQUENCE; Schema: public; Owner: login
--

CREATE SEQUENCE public.auth_permission_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.auth_permission_id_seq OWNER TO login;

--
-- Name: auth_permission_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: login
--

ALTER SEQUENCE public.auth_permission_id_seq OWNED BY public.auth_permission.id;


--
-- Name: auth_user; Type: TABLE; Schema: public; Owner: login
--

CREATE TABLE public.auth_user (
    id integer NOT NULL,
    password character varying(128) NOT NULL,
    last_login timestamp with time zone,
    is_superuser boolean NOT NULL,
    username character varying(150) NOT NULL,
    first_name character varying(150) NOT NULL,
    last_name character varying(150) NOT NULL,
    email character varying(254) NOT NULL,
    is_staff boolean NOT NULL,
    is_active boolean NOT NULL,
    date_joined timestamp with time zone NOT NULL
);


ALTER TABLE public.auth_user OWNER TO login;

--
-- Name: auth_user_groups; Type: TABLE; Schema: public; Owner: login
--

CREATE TABLE public.auth_user_groups (
    id integer NOT NULL,
    user_id integer NOT NULL,
    group_id integer NOT NULL
);


ALTER TABLE public.auth_user_groups OWNER TO login;

--
-- Name: auth_user_groups_id_seq; Type: SEQUENCE; Schema: public; Owner: login
--

CREATE SEQUENCE public.auth_user_groups_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.auth_user_groups_id_seq OWNER TO login;

--
-- Name: auth_user_groups_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: login
--

ALTER SEQUENCE public.auth_user_groups_id_seq OWNED BY public.auth_user_groups.id;


--
-- Name: auth_user_id_seq; Type: SEQUENCE; Schema: public; Owner: login
--

CREATE SEQUENCE public.auth_user_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.auth_user_id_seq OWNER TO login;

--
-- Name: auth_user_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: login
--

ALTER SEQUENCE public.auth_user_id_seq OWNED BY public.auth_user.id;


--
-- Name: auth_user_user_permissions; Type: TABLE; Schema: public; Owner: login
--

CREATE TABLE public.auth_user_user_permissions (
    id integer NOT NULL,
    user_id integer NOT NULL,
    permission_id integer NOT NULL
);


ALTER TABLE public.auth_user_user_permissions OWNER TO login;

--
-- Name: auth_user_user_permissions_id_seq; Type: SEQUENCE; Schema: public; Owner: login
--

CREATE SEQUENCE public.auth_user_user_permissions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.auth_user_user_permissions_id_seq OWNER TO login;

--
-- Name: auth_user_user_permissions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: login
--

ALTER SEQUENCE public.auth_user_user_permissions_id_seq OWNED BY public.auth_user_user_permissions.id;


--
-- Name: authtoken_token; Type: TABLE; Schema: public; Owner: login
--

CREATE TABLE public.authtoken_token (
    key character varying(40) NOT NULL,
    created timestamp with time zone NOT NULL,
    user_id integer NOT NULL
);


ALTER TABLE public.authtoken_token OWNER TO login;

--
-- Name: django_admin_log; Type: TABLE; Schema: public; Owner: login
--

CREATE TABLE public.django_admin_log (
    id integer NOT NULL,
    action_time timestamp with time zone NOT NULL,
    object_id text,
    object_repr character varying(200) NOT NULL,
    action_flag smallint NOT NULL,
    change_message text NOT NULL,
    content_type_id integer,
    user_id integer NOT NULL,
    CONSTRAINT django_admin_log_action_flag_check CHECK ((action_flag >= 0))
);


ALTER TABLE public.django_admin_log OWNER TO login;

--
-- Name: django_admin_log_id_seq; Type: SEQUENCE; Schema: public; Owner: login
--

CREATE SEQUENCE public.django_admin_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.django_admin_log_id_seq OWNER TO login;

--
-- Name: django_admin_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: login
--

ALTER SEQUENCE public.django_admin_log_id_seq OWNED BY public.django_admin_log.id;


--
-- Name: django_content_type; Type: TABLE; Schema: public; Owner: login
--

CREATE TABLE public.django_content_type (
    id integer NOT NULL,
    app_label character varying(100) NOT NULL,
    model character varying(100) NOT NULL
);


ALTER TABLE public.django_content_type OWNER TO login;

--
-- Name: django_content_type_id_seq; Type: SEQUENCE; Schema: public; Owner: login
--

CREATE SEQUENCE public.django_content_type_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.django_content_type_id_seq OWNER TO login;

--
-- Name: django_content_type_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: login
--

ALTER SEQUENCE public.django_content_type_id_seq OWNED BY public.django_content_type.id;


--
-- Name: django_migrations; Type: TABLE; Schema: public; Owner: login
--

CREATE TABLE public.django_migrations (
    id integer NOT NULL,
    app character varying(255) NOT NULL,
    name character varying(255) NOT NULL,
    applied timestamp with time zone NOT NULL
);


ALTER TABLE public.django_migrations OWNER TO login;

--
-- Name: django_migrations_id_seq; Type: SEQUENCE; Schema: public; Owner: login
--

CREATE SEQUENCE public.django_migrations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.django_migrations_id_seq OWNER TO login;

--
-- Name: django_migrations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: login
--

ALTER SEQUENCE public.django_migrations_id_seq OWNED BY public.django_migrations.id;


--
-- Name: django_session; Type: TABLE; Schema: public; Owner: login
--

CREATE TABLE public.django_session (
    session_key character varying(40) NOT NULL,
    session_data text NOT NULL,
    expire_date timestamp with time zone NOT NULL
);


ALTER TABLE public.django_session OWNER TO login;

--
-- Name: GlobalTag id; Type: DEFAULT; Schema: public; Owner: login
--

ALTER TABLE ONLY public."GlobalTag" ALTER COLUMN id SET DEFAULT nextval('public."GlobalTag_id_seq"'::regclass);


--
-- Name: PayloadIOV id; Type: DEFAULT; Schema: public; Owner: login
--

ALTER TABLE ONLY public."PayloadIOV" ALTER COLUMN id SET DEFAULT nextval('public."PayloadIOV_id_seq"'::regclass);


--
-- Name: PayloadList id; Type: DEFAULT; Schema: public; Owner: login
--

ALTER TABLE ONLY public."PayloadList" ALTER COLUMN id SET DEFAULT nextval('public."PayloadList_id_seq"'::regclass);


--
-- Name: auth_group id; Type: DEFAULT; Schema: public; Owner: login
--

ALTER TABLE ONLY public.auth_group ALTER COLUMN id SET DEFAULT nextval('public.auth_group_id_seq'::regclass);


--
-- Name: auth_group_permissions id; Type: DEFAULT; Schema: public; Owner: login
--

ALTER TABLE ONLY public.auth_group_permissions ALTER COLUMN id SET DEFAULT nextval('public.auth_group_permissions_id_seq'::regclass);


--
-- Name: auth_permission id; Type: DEFAULT; Schema: public; Owner: login
--

ALTER TABLE ONLY public.auth_permission ALTER COLUMN id SET DEFAULT nextval('public.auth_permission_id_seq'::regclass);


--
-- Name: auth_user id; Type: DEFAULT; Schema: public; Owner: login
--

ALTER TABLE ONLY public.auth_user ALTER COLUMN id SET DEFAULT nextval('public.auth_user_id_seq'::regclass);


--
-- Name: auth_user_groups id; Type: DEFAULT; Schema: public; Owner: login
--

ALTER TABLE ONLY public.auth_user_groups ALTER COLUMN id SET DEFAULT nextval('public.auth_user_groups_id_seq'::regclass);


--
-- Name: auth_user_user_permissions id; Type: DEFAULT; Schema: public; Owner: login
--

ALTER TABLE ONLY public.auth_user_user_permissions ALTER COLUMN id SET DEFAULT nextval('public.auth_user_user_permissions_id_seq'::regclass);


--
-- Name: django_admin_log id; Type: DEFAULT; Schema: public; Owner: login
--

ALTER TABLE ONLY public.django_admin_log ALTER COLUMN id SET DEFAULT nextval('public.django_admin_log_id_seq'::regclass);


--
-- Name: django_content_type id; Type: DEFAULT; Schema: public; Owner: login
--

ALTER TABLE ONLY public.django_content_type ALTER COLUMN id SET DEFAULT nextval('public.django_content_type_id_seq'::regclass);


--
-- Name: django_migrations id; Type: DEFAULT; Schema: public; Owner: login
--

ALTER TABLE ONLY public.django_migrations ALTER COLUMN id SET DEFAULT nextval('public.django_migrations_id_seq'::regclass);


--
-- Data for Name: GlobalTag; Type: TABLE DATA; Schema: public; Owner: login
--

COPY public."GlobalTag" (id, name, description, created, updated, status_id, type_id) FROM stdin;
1	TestSmallGT2		2021-10-14 19:23:50.864422+00	2021-10-14 19:23:50.864442+00	1	1
\.


--
-- Data for Name: GlobalTagStatus; Type: TABLE DATA; Schema: public; Owner: login
--

COPY public."GlobalTagStatus" (id, name, description, created) FROM stdin;
1	test		2021-10-14 19:23:50.802726+00
\.


--
-- Data for Name: GlobalTagType; Type: TABLE DATA; Schema: public; Owner: login
--

COPY public."GlobalTagType" (id, name, description, created) FROM stdin;
1	test		2021-10-14 19:23:50.771583+00
\.


--
-- Data for Name: PayloadIOV; Type: TABLE DATA; Schema: public; Owner: login
--

COPY public."PayloadIOV" (id, payload_url, major_iov, minor_iov, description, created, updated, payload_list_id) FROM stdin;
1	TestSmallGT2Payload0_1	0	1634239431		2021-10-14 19:23:51.207546+00	2021-10-14 19:23:51.207584+00	1
2	TestSmallGT2Payload0_2	0	1634239431		2021-10-14 19:23:51.240577+00	2021-10-14 19:23:51.240598+00	2
3	TestSmallGT2Payload0_3	0	1634239431		2021-10-14 19:23:51.264328+00	2021-10-14 19:23:51.264344+00	3
4	TestSmallGT2Payload0_4	0	1634239431		2021-10-14 19:23:51.287578+00	2021-10-14 19:23:51.287598+00	4
5	TestSmallGT2Payload0_5	0	1634239431		2021-10-14 19:23:51.312709+00	2021-10-14 19:23:51.312721+00	5
6	TestSmallGT2Payload0_6	0	1634239431		2021-10-14 19:23:51.336364+00	2021-10-14 19:23:51.336376+00	6
7	TestSmallGT2Payload0_7	0	1634239431		2021-10-14 19:23:51.360408+00	2021-10-14 19:23:51.360428+00	7
8	TestSmallGT2Payload0_8	0	1634239431		2021-10-14 19:23:51.384977+00	2021-10-14 19:23:51.384996+00	8
9	TestSmallGT2Payload0_9	0	1634239431		2021-10-14 19:23:51.41292+00	2021-10-14 19:23:51.412974+00	9
10	TestSmallGT2Payload0_10	0	1634239431		2021-10-14 19:23:51.43644+00	2021-10-14 19:23:51.436478+00	10
11	TestSmallGT2Payload1_1	0	1634239432		2021-10-14 19:23:51.464033+00	2021-10-14 19:23:51.464053+00	1
12	TestSmallGT2Payload1_2	0	1634239432		2021-10-14 19:23:51.487865+00	2021-10-14 19:23:51.487886+00	2
13	TestSmallGT2Payload1_3	0	1634239432		2021-10-14 19:23:51.516881+00	2021-10-14 19:23:51.516902+00	3
14	TestSmallGT2Payload1_4	0	1634239432		2021-10-14 19:23:51.542299+00	2021-10-14 19:23:51.542324+00	4
15	TestSmallGT2Payload1_5	0	1634239432		2021-10-14 19:23:51.568168+00	2021-10-14 19:23:51.568187+00	5
16	TestSmallGT2Payload1_6	0	1634239432		2021-10-14 19:23:51.591278+00	2021-10-14 19:23:51.591294+00	6
17	TestSmallGT2Payload1_7	0	1634239432		2021-10-14 19:23:51.615627+00	2021-10-14 19:23:51.615644+00	7
18	TestSmallGT2Payload1_8	0	1634239432		2021-10-14 19:23:51.639121+00	2021-10-14 19:23:51.63914+00	8
19	TestSmallGT2Payload1_9	0	1634239432		2021-10-14 19:23:51.663868+00	2021-10-14 19:23:51.663883+00	9
20	TestSmallGT2Payload1_10	0	1634239432		2021-10-14 19:23:51.691493+00	2021-10-14 19:23:51.691509+00	10
21	TestSmallGT2Payload2_1	0	1634239433		2021-10-14 19:23:51.718591+00	2021-10-14 19:23:51.718624+00	1
22	TestSmallGT2Payload2_2	0	1634239433		2021-10-14 19:23:51.74472+00	2021-10-14 19:23:51.744739+00	2
23	TestSmallGT2Payload2_3	0	1634239433		2021-10-14 19:23:51.768498+00	2021-10-14 19:23:51.768518+00	3
24	TestSmallGT2Payload2_4	0	1634239433		2021-10-14 19:23:51.790821+00	2021-10-14 19:23:51.790842+00	4
25	TestSmallGT2Payload2_5	0	1634239433		2021-10-14 19:23:51.813397+00	2021-10-14 19:23:51.813408+00	5
26	TestSmallGT2Payload2_6	0	1634239433		2021-10-14 19:23:51.836477+00	2021-10-14 19:23:51.836497+00	6
27	TestSmallGT2Payload2_7	0	1634239433		2021-10-14 19:23:51.859367+00	2021-10-14 19:23:51.859386+00	7
28	TestSmallGT2Payload2_8	0	1634239433		2021-10-14 19:23:51.883914+00	2021-10-14 19:23:51.883982+00	8
29	TestSmallGT2Payload2_9	0	1634239433		2021-10-14 19:23:51.90939+00	2021-10-14 19:23:51.90941+00	9
30	TestSmallGT2Payload2_10	0	1634239433		2021-10-14 19:23:51.93284+00	2021-10-14 19:23:51.932859+00	10
31	TestSmallGT2Payload3_1	0	1634239434		2021-10-14 19:23:51.956881+00	2021-10-14 19:23:51.956902+00	1
32	TestSmallGT2Payload3_2	0	1634239434		2021-10-14 19:23:51.981327+00	2021-10-14 19:23:51.981347+00	2
33	TestSmallGT2Payload3_3	0	1634239434		2021-10-14 19:23:52.005178+00	2021-10-14 19:23:52.005199+00	3
34	TestSmallGT2Payload3_4	0	1634239434		2021-10-14 19:23:52.033286+00	2021-10-14 19:23:52.033306+00	4
35	TestSmallGT2Payload3_5	0	1634239434		2021-10-14 19:23:52.057829+00	2021-10-14 19:23:52.057845+00	5
36	TestSmallGT2Payload3_6	0	1634239434		2021-10-14 19:23:52.081786+00	2021-10-14 19:23:52.081805+00	6
37	TestSmallGT2Payload3_7	0	1634239434		2021-10-14 19:23:52.108337+00	2021-10-14 19:23:52.108358+00	7
38	TestSmallGT2Payload3_8	0	1634239434		2021-10-14 19:23:52.134793+00	2021-10-14 19:23:52.134812+00	8
39	TestSmallGT2Payload3_9	0	1634239434		2021-10-14 19:23:52.157492+00	2021-10-14 19:23:52.157513+00	9
40	TestSmallGT2Payload3_10	0	1634239434		2021-10-14 19:23:52.183315+00	2021-10-14 19:23:52.183335+00	10
41	TestSmallGT2Payload4_1	0	1634239435		2021-10-14 19:23:52.207315+00	2021-10-14 19:23:52.207335+00	1
42	TestSmallGT2Payload4_2	0	1634239435		2021-10-14 19:23:52.231875+00	2021-10-14 19:23:52.231889+00	2
43	TestSmallGT2Payload4_3	0	1634239435		2021-10-14 19:23:52.255009+00	2021-10-14 19:23:52.255078+00	3
44	TestSmallGT2Payload4_4	0	1634239435		2021-10-14 19:23:52.278259+00	2021-10-14 19:23:52.278279+00	4
45	TestSmallGT2Payload4_5	0	1634239435		2021-10-14 19:23:52.301907+00	2021-10-14 19:23:52.301926+00	5
46	TestSmallGT2Payload4_6	0	1634239435		2021-10-14 19:23:52.325379+00	2021-10-14 19:23:52.325393+00	6
47	TestSmallGT2Payload4_7	0	1634239435		2021-10-14 19:23:52.348783+00	2021-10-14 19:23:52.348802+00	7
48	TestSmallGT2Payload4_8	0	1634239435		2021-10-14 19:23:52.371688+00	2021-10-14 19:23:52.371705+00	8
49	TestSmallGT2Payload4_9	0	1634239435		2021-10-14 19:23:52.395418+00	2021-10-14 19:23:52.395438+00	9
50	TestSmallGT2Payload4_10	0	1634239435		2021-10-14 19:23:52.418718+00	2021-10-14 19:23:52.418737+00	10
51	TestSmallGT2Payload5_1	0	1634239436		2021-10-14 19:23:52.441542+00	2021-10-14 19:23:52.441562+00	1
52	TestSmallGT2Payload5_2	0	1634239436		2021-10-14 19:23:52.464593+00	2021-10-14 19:23:52.46461+00	2
53	TestSmallGT2Payload5_3	0	1634239436		2021-10-14 19:23:52.487618+00	2021-10-14 19:23:52.487637+00	3
54	TestSmallGT2Payload5_4	0	1634239436		2021-10-14 19:23:52.511245+00	2021-10-14 19:23:52.511266+00	4
55	TestSmallGT2Payload5_5	0	1634239436		2021-10-14 19:23:52.539737+00	2021-10-14 19:23:52.539757+00	5
56	TestSmallGT2Payload5_6	0	1634239436		2021-10-14 19:23:52.563881+00	2021-10-14 19:23:52.5639+00	6
57	TestSmallGT2Payload5_7	0	1634239436		2021-10-14 19:23:52.588553+00	2021-10-14 19:23:52.588566+00	7
58	TestSmallGT2Payload5_8	0	1634239436		2021-10-14 19:23:52.611828+00	2021-10-14 19:23:52.611865+00	8
59	TestSmallGT2Payload5_9	0	1634239436		2021-10-14 19:23:52.63561+00	2021-10-14 19:23:52.635631+00	9
60	TestSmallGT2Payload5_10	0	1634239436		2021-10-14 19:23:52.659084+00	2021-10-14 19:23:52.659097+00	10
61	TestSmallGT2Payload6_1	0	1634239437		2021-10-14 19:23:52.683111+00	2021-10-14 19:23:52.683131+00	1
62	TestSmallGT2Payload6_2	0	1634239437		2021-10-14 19:23:52.706236+00	2021-10-14 19:23:52.706256+00	2
63	TestSmallGT2Payload6_3	0	1634239437		2021-10-14 19:23:52.729774+00	2021-10-14 19:23:52.729795+00	3
64	TestSmallGT2Payload6_4	0	1634239437		2021-10-14 19:23:52.753171+00	2021-10-14 19:23:52.753189+00	4
65	TestSmallGT2Payload6_5	0	1634239437		2021-10-14 19:23:52.77869+00	2021-10-14 19:23:52.778727+00	5
66	TestSmallGT2Payload6_6	0	1634239437		2021-10-14 19:23:52.803963+00	2021-10-14 19:23:52.803982+00	6
67	TestSmallGT2Payload6_7	0	1634239437		2021-10-14 19:23:52.828467+00	2021-10-14 19:23:52.828487+00	7
68	TestSmallGT2Payload6_8	0	1634239437		2021-10-14 19:23:52.852664+00	2021-10-14 19:23:52.852701+00	8
69	TestSmallGT2Payload6_9	0	1634239437		2021-10-14 19:23:52.876885+00	2021-10-14 19:23:52.876904+00	9
70	TestSmallGT2Payload6_10	0	1634239437		2021-10-14 19:23:52.901254+00	2021-10-14 19:23:52.90127+00	10
71	TestSmallGT2Payload7_1	0	1634239438		2021-10-14 19:23:52.924367+00	2021-10-14 19:23:52.924389+00	1
72	TestSmallGT2Payload7_2	0	1634239438		2021-10-14 19:23:52.94773+00	2021-10-14 19:23:52.947743+00	2
73	TestSmallGT2Payload7_3	0	1634239438		2021-10-14 19:23:52.971436+00	2021-10-14 19:23:52.971455+00	3
74	TestSmallGT2Payload7_4	0	1634239438		2021-10-14 19:23:52.993997+00	2021-10-14 19:23:52.994009+00	4
75	TestSmallGT2Payload7_5	0	1634239438		2021-10-14 19:23:53.018274+00	2021-10-14 19:23:53.018293+00	5
76	TestSmallGT2Payload7_6	0	1634239438		2021-10-14 19:23:53.041631+00	2021-10-14 19:23:53.041651+00	6
77	TestSmallGT2Payload7_7	0	1634239438		2021-10-14 19:23:53.071679+00	2021-10-14 19:23:53.071736+00	7
78	TestSmallGT2Payload7_8	0	1634239438		2021-10-14 19:23:53.096697+00	2021-10-14 19:23:53.096767+00	8
79	TestSmallGT2Payload7_9	0	1634239438		2021-10-14 19:23:53.121003+00	2021-10-14 19:23:53.121023+00	9
80	TestSmallGT2Payload7_10	0	1634239438		2021-10-14 19:23:53.143781+00	2021-10-14 19:23:53.1438+00	10
81	TestSmallGT2Payload8_1	0	1634239439		2021-10-14 19:23:53.167819+00	2021-10-14 19:23:53.167836+00	1
82	TestSmallGT2Payload8_2	0	1634239439		2021-10-14 19:23:53.191791+00	2021-10-14 19:23:53.191811+00	2
83	TestSmallGT2Payload8_3	0	1634239439		2021-10-14 19:23:53.217048+00	2021-10-14 19:23:53.217086+00	3
84	TestSmallGT2Payload8_4	0	1634239439		2021-10-14 19:23:53.240854+00	2021-10-14 19:23:53.240873+00	4
85	TestSmallGT2Payload8_5	0	1634239439		2021-10-14 19:23:53.265681+00	2021-10-14 19:23:53.265698+00	5
86	TestSmallGT2Payload8_6	0	1634239439		2021-10-14 19:23:53.290546+00	2021-10-14 19:23:53.290562+00	6
87	TestSmallGT2Payload8_7	0	1634239439		2021-10-14 19:23:53.315354+00	2021-10-14 19:23:53.315366+00	7
88	TestSmallGT2Payload8_8	0	1634239439		2021-10-14 19:23:53.339222+00	2021-10-14 19:23:53.339242+00	8
89	TestSmallGT2Payload8_9	0	1634239439		2021-10-14 19:23:53.365119+00	2021-10-14 19:23:53.365139+00	9
90	TestSmallGT2Payload8_10	0	1634239439		2021-10-14 19:23:53.388773+00	2021-10-14 19:23:53.388793+00	10
91	TestSmallGT2Payload9_1	0	1634239440		2021-10-14 19:23:53.41233+00	2021-10-14 19:23:53.412351+00	1
92	TestSmallGT2Payload9_2	0	1634239440		2021-10-14 19:23:53.436533+00	2021-10-14 19:23:53.436553+00	2
93	TestSmallGT2Payload9_3	0	1634239440		2021-10-14 19:23:53.459899+00	2021-10-14 19:23:53.459918+00	3
94	TestSmallGT2Payload9_4	0	1634239440		2021-10-14 19:23:53.485541+00	2021-10-14 19:23:53.485562+00	4
95	TestSmallGT2Payload9_5	0	1634239440		2021-10-14 19:23:53.511624+00	2021-10-14 19:23:53.511644+00	5
96	TestSmallGT2Payload9_6	0	1634239440		2021-10-14 19:23:53.535449+00	2021-10-14 19:23:53.535468+00	6
97	TestSmallGT2Payload9_7	0	1634239440		2021-10-14 19:23:53.56126+00	2021-10-14 19:23:53.56128+00	7
98	TestSmallGT2Payload9_8	0	1634239440		2021-10-14 19:23:53.58613+00	2021-10-14 19:23:53.58615+00	8
99	TestSmallGT2Payload9_9	0	1634239440		2021-10-14 19:23:53.610219+00	2021-10-14 19:23:53.610239+00	9
100	TestSmallGT2Payload9_10	0	1634239440		2021-10-14 19:23:53.634458+00	2021-10-14 19:23:53.634478+00	10
\.


--
-- Data for Name: PayloadList; Type: TABLE DATA; Schema: public; Owner: login
--

COPY public."PayloadList" (id, name, description, created, updated, global_tag_id, payload_type_id) FROM stdin;
1	TestSmallGT2List0		2021-10-14 19:23:50.912277+00	2021-10-14 19:23:50.912296+00	1	1
2	TestSmallGT2List1		2021-10-14 19:23:50.953662+00	2021-10-14 19:23:50.953683+00	1	1
3	TestSmallGT2List2		2021-10-14 19:23:50.984414+00	2021-10-14 19:23:50.984435+00	1	1
4	TestSmallGT2List3		2021-10-14 19:23:51.013862+00	2021-10-14 19:23:51.013883+00	1	1
5	TestSmallGT2List4		2021-10-14 19:23:51.042896+00	2021-10-14 19:23:51.042916+00	1	1
6	TestSmallGT2List5		2021-10-14 19:23:51.072455+00	2021-10-14 19:23:51.072472+00	1	1
7	TestSmallGT2List6		2021-10-14 19:23:51.101021+00	2021-10-14 19:23:51.101041+00	1	1
8	TestSmallGT2List7		2021-10-14 19:23:51.128233+00	2021-10-14 19:23:51.128254+00	1	1
9	TestSmallGT2List8		2021-10-14 19:23:51.155673+00	2021-10-14 19:23:51.155693+00	1	1
10	TestSmallGT2List9		2021-10-14 19:23:51.182107+00	2021-10-14 19:23:51.182126+00	1	1
\.


--
-- Data for Name: PayloadType; Type: TABLE DATA; Schema: public; Owner: login
--

COPY public."PayloadType" (id, name, description, created) FROM stdin;
1	test		2021-10-14 19:23:50.831965+00
\.


--
-- Data for Name: auth_group; Type: TABLE DATA; Schema: public; Owner: login
--

COPY public.auth_group (id, name) FROM stdin;
\.


--
-- Data for Name: auth_group_permissions; Type: TABLE DATA; Schema: public; Owner: login
--

COPY public.auth_group_permissions (id, group_id, permission_id) FROM stdin;
\.


--
-- Data for Name: auth_permission; Type: TABLE DATA; Schema: public; Owner: login
--

COPY public.auth_permission (id, name, content_type_id, codename) FROM stdin;
1	Can add log entry	1	add_logentry
2	Can change log entry	1	change_logentry
3	Can delete log entry	1	delete_logentry
4	Can view log entry	1	view_logentry
5	Can add permission	2	add_permission
6	Can change permission	2	change_permission
7	Can delete permission	2	delete_permission
8	Can view permission	2	view_permission
9	Can add group	3	add_group
10	Can change group	3	change_group
11	Can delete group	3	delete_group
12	Can view group	3	view_group
13	Can add user	4	add_user
14	Can change user	4	change_user
15	Can delete user	4	delete_user
16	Can view user	4	view_user
17	Can add content type	5	add_contenttype
18	Can change content type	5	change_contenttype
19	Can delete content type	5	delete_contenttype
20	Can view content type	5	view_contenttype
21	Can add session	6	add_session
22	Can change session	6	change_session
23	Can delete session	6	delete_session
24	Can view session	6	view_session
25	Can add Token	7	add_token
26	Can change Token	7	change_token
27	Can delete Token	7	delete_token
28	Can view Token	7	view_token
29	Can add token	8	add_tokenproxy
30	Can change token	8	change_tokenproxy
31	Can delete token	8	delete_tokenproxy
32	Can view token	8	view_tokenproxy
33	Can add global tag	9	add_globaltag
34	Can change global tag	9	change_globaltag
35	Can delete global tag	9	delete_globaltag
36	Can view global tag	9	view_globaltag
37	Can add global tag status	10	add_globaltagstatus
38	Can change global tag status	10	change_globaltagstatus
39	Can delete global tag status	10	delete_globaltagstatus
40	Can view global tag status	10	view_globaltagstatus
41	Can add global tag type	11	add_globaltagtype
42	Can change global tag type	11	change_globaltagtype
43	Can delete global tag type	11	delete_globaltagtype
44	Can view global tag type	11	view_globaltagtype
45	Can add payload type	12	add_payloadtype
46	Can change payload type	12	change_payloadtype
47	Can delete payload type	12	delete_payloadtype
48	Can view payload type	12	view_payloadtype
49	Can add payload list	13	add_payloadlist
50	Can change payload list	13	change_payloadlist
51	Can delete payload list	13	delete_payloadlist
52	Can view payload list	13	view_payloadlist
53	Can add payload iov	14	add_payloadiov
54	Can change payload iov	14	change_payloadiov
55	Can delete payload iov	14	delete_payloadiov
56	Can view payload iov	14	view_payloadiov
\.


--
-- Data for Name: auth_user; Type: TABLE DATA; Schema: public; Owner: login
--

COPY public.auth_user (id, password, last_login, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined) FROM stdin;
\.


--
-- Data for Name: auth_user_groups; Type: TABLE DATA; Schema: public; Owner: login
--

COPY public.auth_user_groups (id, user_id, group_id) FROM stdin;
\.


--
-- Data for Name: auth_user_user_permissions; Type: TABLE DATA; Schema: public; Owner: login
--

COPY public.auth_user_user_permissions (id, user_id, permission_id) FROM stdin;
\.


--
-- Data for Name: authtoken_token; Type: TABLE DATA; Schema: public; Owner: login
--

COPY public.authtoken_token (key, created, user_id) FROM stdin;
\.


--
-- Data for Name: django_admin_log; Type: TABLE DATA; Schema: public; Owner: login
--

COPY public.django_admin_log (id, action_time, object_id, object_repr, action_flag, change_message, content_type_id, user_id) FROM stdin;
\.


--
-- Data for Name: django_content_type; Type: TABLE DATA; Schema: public; Owner: login
--

COPY public.django_content_type (id, app_label, model) FROM stdin;
1	admin	logentry
2	auth	permission
3	auth	group
4	auth	user
5	contenttypes	contenttype
6	sessions	session
7	authtoken	token
8	authtoken	tokenproxy
9	cdb_rest	globaltag
10	cdb_rest	globaltagstatus
11	cdb_rest	globaltagtype
12	cdb_rest	payloadtype
13	cdb_rest	payloadlist
14	cdb_rest	payloadiov
\.


--
-- Data for Name: django_migrations; Type: TABLE DATA; Schema: public; Owner: login
--

COPY public.django_migrations (id, app, name, applied) FROM stdin;
1	contenttypes	0001_initial	2021-10-14 18:40:08.704591+00
2	auth	0001_initial	2021-10-14 18:40:08.956083+00
3	admin	0001_initial	2021-10-14 18:40:09.021541+00
4	admin	0002_logentry_remove_auto_add	2021-10-14 18:40:09.02922+00
5	admin	0003_logentry_add_action_flag_choices	2021-10-14 18:40:09.03678+00
6	contenttypes	0002_remove_content_type_name	2021-10-14 18:40:09.06069+00
7	auth	0002_alter_permission_name_max_length	2021-10-14 18:40:09.068252+00
8	auth	0003_alter_user_email_max_length	2021-10-14 18:40:09.075956+00
9	auth	0004_alter_user_username_opts	2021-10-14 18:40:09.083878+00
10	auth	0005_alter_user_last_login_null	2021-10-14 18:40:09.091251+00
11	auth	0006_require_contenttypes_0002	2021-10-14 18:40:09.093617+00
12	auth	0007_alter_validators_add_error_messages	2021-10-14 18:40:09.101124+00
13	auth	0008_alter_user_username_max_length	2021-10-14 18:40:09.127189+00
14	auth	0009_alter_user_last_name_max_length	2021-10-14 18:40:09.136291+00
15	auth	0010_alter_group_name_max_length	2021-10-14 18:40:09.146737+00
16	auth	0011_update_proxy_permissions	2021-10-14 18:40:09.153644+00
17	auth	0012_alter_user_first_name_max_length	2021-10-14 18:40:09.160931+00
18	authtoken	0001_initial	2021-10-14 18:40:09.196331+00
19	authtoken	0002_auto_20160226_1747	2021-10-14 18:40:09.21858+00
20	authtoken	0003_tokenproxy	2021-10-14 18:40:09.222348+00
21	cdb_rest	0001_initial	2021-10-14 18:40:09.405494+00
22	sessions	0001_initial	2021-10-14 18:40:09.439708+00
\.


--
-- Data for Name: django_session; Type: TABLE DATA; Schema: public; Owner: login
--

COPY public.django_session (session_key, session_data, expire_date) FROM stdin;
\.


--
-- Name: GlobalTag_id_seq; Type: SEQUENCE SET; Schema: public; Owner: login
--

SELECT pg_catalog.setval('public."GlobalTag_id_seq"', 1, true);


--
-- Name: PayloadIOV_id_seq; Type: SEQUENCE SET; Schema: public; Owner: login
--

SELECT pg_catalog.setval('public."PayloadIOV_id_seq"', 100, true);


--
-- Name: PayloadList_id_seq; Type: SEQUENCE SET; Schema: public; Owner: login
--

SELECT pg_catalog.setval('public."PayloadList_id_seq"', 10, true);


--
-- Name: auth_group_id_seq; Type: SEQUENCE SET; Schema: public; Owner: login
--

SELECT pg_catalog.setval('public.auth_group_id_seq', 1, false);


--
-- Name: auth_group_permissions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: login
--

SELECT pg_catalog.setval('public.auth_group_permissions_id_seq', 1, false);


--
-- Name: auth_permission_id_seq; Type: SEQUENCE SET; Schema: public; Owner: login
--

SELECT pg_catalog.setval('public.auth_permission_id_seq', 56, true);


--
-- Name: auth_user_groups_id_seq; Type: SEQUENCE SET; Schema: public; Owner: login
--

SELECT pg_catalog.setval('public.auth_user_groups_id_seq', 1, false);


--
-- Name: auth_user_id_seq; Type: SEQUENCE SET; Schema: public; Owner: login
--

SELECT pg_catalog.setval('public.auth_user_id_seq', 1, false);


--
-- Name: auth_user_user_permissions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: login
--

SELECT pg_catalog.setval('public.auth_user_user_permissions_id_seq', 1, false);


--
-- Name: django_admin_log_id_seq; Type: SEQUENCE SET; Schema: public; Owner: login
--

SELECT pg_catalog.setval('public.django_admin_log_id_seq', 1, false);


--
-- Name: django_content_type_id_seq; Type: SEQUENCE SET; Schema: public; Owner: login
--

SELECT pg_catalog.setval('public.django_content_type_id_seq', 14, true);


--
-- Name: django_migrations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: login
--

SELECT pg_catalog.setval('public.django_migrations_id_seq', 22, true);


--
-- Name: GlobalTagStatus GlobalTagStatus_pkey; Type: CONSTRAINT; Schema: public; Owner: login
--

ALTER TABLE ONLY public."GlobalTagStatus"
    ADD CONSTRAINT "GlobalTagStatus_pkey" PRIMARY KEY (id);


--
-- Name: GlobalTagType GlobalTagType_name_key; Type: CONSTRAINT; Schema: public; Owner: login
--

ALTER TABLE ONLY public."GlobalTagType"
    ADD CONSTRAINT "GlobalTagType_name_key" UNIQUE (name);


--
-- Name: GlobalTagType GlobalTagType_pkey; Type: CONSTRAINT; Schema: public; Owner: login
--

ALTER TABLE ONLY public."GlobalTagType"
    ADD CONSTRAINT "GlobalTagType_pkey" PRIMARY KEY (id);


--
-- Name: GlobalTag GlobalTag_pkey; Type: CONSTRAINT; Schema: public; Owner: login
--

ALTER TABLE ONLY public."GlobalTag"
    ADD CONSTRAINT "GlobalTag_pkey" PRIMARY KEY (id);


--
-- Name: PayloadIOV PayloadIOV_pkey; Type: CONSTRAINT; Schema: public; Owner: login
--

ALTER TABLE ONLY public."PayloadIOV"
    ADD CONSTRAINT "PayloadIOV_pkey" PRIMARY KEY (id);


--
-- Name: PayloadList PayloadList_pkey; Type: CONSTRAINT; Schema: public; Owner: login
--

ALTER TABLE ONLY public."PayloadList"
    ADD CONSTRAINT "PayloadList_pkey" PRIMARY KEY (id);


--
-- Name: PayloadType PayloadType_name_key; Type: CONSTRAINT; Schema: public; Owner: login
--

ALTER TABLE ONLY public."PayloadType"
    ADD CONSTRAINT "PayloadType_name_key" UNIQUE (name);


--
-- Name: PayloadType PayloadType_pkey; Type: CONSTRAINT; Schema: public; Owner: login
--

ALTER TABLE ONLY public."PayloadType"
    ADD CONSTRAINT "PayloadType_pkey" PRIMARY KEY (id);


--
-- Name: auth_group auth_group_name_key; Type: CONSTRAINT; Schema: public; Owner: login
--

ALTER TABLE ONLY public.auth_group
    ADD CONSTRAINT auth_group_name_key UNIQUE (name);


--
-- Name: auth_group_permissions auth_group_permissions_group_id_permission_id_0cd325b0_uniq; Type: CONSTRAINT; Schema: public; Owner: login
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_group_id_permission_id_0cd325b0_uniq UNIQUE (group_id, permission_id);


--
-- Name: auth_group_permissions auth_group_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: login
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_pkey PRIMARY KEY (id);


--
-- Name: auth_group auth_group_pkey; Type: CONSTRAINT; Schema: public; Owner: login
--

ALTER TABLE ONLY public.auth_group
    ADD CONSTRAINT auth_group_pkey PRIMARY KEY (id);


--
-- Name: auth_permission auth_permission_content_type_id_codename_01ab375a_uniq; Type: CONSTRAINT; Schema: public; Owner: login
--

ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_content_type_id_codename_01ab375a_uniq UNIQUE (content_type_id, codename);


--
-- Name: auth_permission auth_permission_pkey; Type: CONSTRAINT; Schema: public; Owner: login
--

ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_pkey PRIMARY KEY (id);


--
-- Name: auth_user_groups auth_user_groups_pkey; Type: CONSTRAINT; Schema: public; Owner: login
--

ALTER TABLE ONLY public.auth_user_groups
    ADD CONSTRAINT auth_user_groups_pkey PRIMARY KEY (id);


--
-- Name: auth_user_groups auth_user_groups_user_id_group_id_94350c0c_uniq; Type: CONSTRAINT; Schema: public; Owner: login
--

ALTER TABLE ONLY public.auth_user_groups
    ADD CONSTRAINT auth_user_groups_user_id_group_id_94350c0c_uniq UNIQUE (user_id, group_id);


--
-- Name: auth_user auth_user_pkey; Type: CONSTRAINT; Schema: public; Owner: login
--

ALTER TABLE ONLY public.auth_user
    ADD CONSTRAINT auth_user_pkey PRIMARY KEY (id);


--
-- Name: auth_user_user_permissions auth_user_user_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: login
--

ALTER TABLE ONLY public.auth_user_user_permissions
    ADD CONSTRAINT auth_user_user_permissions_pkey PRIMARY KEY (id);


--
-- Name: auth_user_user_permissions auth_user_user_permissions_user_id_permission_id_14a6b632_uniq; Type: CONSTRAINT; Schema: public; Owner: login
--

ALTER TABLE ONLY public.auth_user_user_permissions
    ADD CONSTRAINT auth_user_user_permissions_user_id_permission_id_14a6b632_uniq UNIQUE (user_id, permission_id);


--
-- Name: auth_user auth_user_username_key; Type: CONSTRAINT; Schema: public; Owner: login
--

ALTER TABLE ONLY public.auth_user
    ADD CONSTRAINT auth_user_username_key UNIQUE (username);


--
-- Name: authtoken_token authtoken_token_pkey; Type: CONSTRAINT; Schema: public; Owner: login
--

ALTER TABLE ONLY public.authtoken_token
    ADD CONSTRAINT authtoken_token_pkey PRIMARY KEY (key);


--
-- Name: authtoken_token authtoken_token_user_id_key; Type: CONSTRAINT; Schema: public; Owner: login
--

ALTER TABLE ONLY public.authtoken_token
    ADD CONSTRAINT authtoken_token_user_id_key UNIQUE (user_id);


--
-- Name: django_admin_log django_admin_log_pkey; Type: CONSTRAINT; Schema: public; Owner: login
--

ALTER TABLE ONLY public.django_admin_log
    ADD CONSTRAINT django_admin_log_pkey PRIMARY KEY (id);


--
-- Name: django_content_type django_content_type_app_label_model_76bd3d3b_uniq; Type: CONSTRAINT; Schema: public; Owner: login
--

ALTER TABLE ONLY public.django_content_type
    ADD CONSTRAINT django_content_type_app_label_model_76bd3d3b_uniq UNIQUE (app_label, model);


--
-- Name: django_content_type django_content_type_pkey; Type: CONSTRAINT; Schema: public; Owner: login
--

ALTER TABLE ONLY public.django_content_type
    ADD CONSTRAINT django_content_type_pkey PRIMARY KEY (id);


--
-- Name: django_migrations django_migrations_pkey; Type: CONSTRAINT; Schema: public; Owner: login
--

ALTER TABLE ONLY public.django_migrations
    ADD CONSTRAINT django_migrations_pkey PRIMARY KEY (id);


--
-- Name: django_session django_session_pkey; Type: CONSTRAINT; Schema: public; Owner: login
--

ALTER TABLE ONLY public.django_session
    ADD CONSTRAINT django_session_pkey PRIMARY KEY (session_key);


--
-- Name: GlobalTagType_name_f8ca36fe_like; Type: INDEX; Schema: public; Owner: login
--

CREATE INDEX "GlobalTagType_name_f8ca36fe_like" ON public."GlobalTagType" USING btree (name varchar_pattern_ops);


--
-- Name: GlobalTag_status_id_7b5018a3; Type: INDEX; Schema: public; Owner: login
--

CREATE INDEX "GlobalTag_status_id_7b5018a3" ON public."GlobalTag" USING btree (status_id);


--
-- Name: GlobalTag_type_id_36cf70c0; Type: INDEX; Schema: public; Owner: login
--

CREATE INDEX "GlobalTag_type_id_36cf70c0" ON public."GlobalTag" USING btree (type_id);


--
-- Name: PayloadIOV_payload_list_id_37321d74; Type: INDEX; Schema: public; Owner: login
--

CREATE INDEX "PayloadIOV_payload_list_id_37321d74" ON public."PayloadIOV" USING btree (payload_list_id);


--
-- Name: PayloadList_global_tag_id_2b35c85f; Type: INDEX; Schema: public; Owner: login
--

CREATE INDEX "PayloadList_global_tag_id_2b35c85f" ON public."PayloadList" USING btree (global_tag_id);


--
-- Name: PayloadList_payload_type_id_7d588918; Type: INDEX; Schema: public; Owner: login
--

CREATE INDEX "PayloadList_payload_type_id_7d588918" ON public."PayloadList" USING btree (payload_type_id);


--
-- Name: PayloadType_name_3fbebe58_like; Type: INDEX; Schema: public; Owner: login
--

CREATE INDEX "PayloadType_name_3fbebe58_like" ON public."PayloadType" USING btree (name varchar_pattern_ops);


--
-- Name: auth_group_name_a6ea08ec_like; Type: INDEX; Schema: public; Owner: login
--

CREATE INDEX auth_group_name_a6ea08ec_like ON public.auth_group USING btree (name varchar_pattern_ops);


--
-- Name: auth_group_permissions_group_id_b120cbf9; Type: INDEX; Schema: public; Owner: login
--

CREATE INDEX auth_group_permissions_group_id_b120cbf9 ON public.auth_group_permissions USING btree (group_id);


--
-- Name: auth_group_permissions_permission_id_84c5c92e; Type: INDEX; Schema: public; Owner: login
--

CREATE INDEX auth_group_permissions_permission_id_84c5c92e ON public.auth_group_permissions USING btree (permission_id);


--
-- Name: auth_permission_content_type_id_2f476e4b; Type: INDEX; Schema: public; Owner: login
--

CREATE INDEX auth_permission_content_type_id_2f476e4b ON public.auth_permission USING btree (content_type_id);


--
-- Name: auth_user_groups_group_id_97559544; Type: INDEX; Schema: public; Owner: login
--

CREATE INDEX auth_user_groups_group_id_97559544 ON public.auth_user_groups USING btree (group_id);


--
-- Name: auth_user_groups_user_id_6a12ed8b; Type: INDEX; Schema: public; Owner: login
--

CREATE INDEX auth_user_groups_user_id_6a12ed8b ON public.auth_user_groups USING btree (user_id);


--
-- Name: auth_user_user_permissions_permission_id_1fbb5f2c; Type: INDEX; Schema: public; Owner: login
--

CREATE INDEX auth_user_user_permissions_permission_id_1fbb5f2c ON public.auth_user_user_permissions USING btree (permission_id);


--
-- Name: auth_user_user_permissions_user_id_a95ead1b; Type: INDEX; Schema: public; Owner: login
--

CREATE INDEX auth_user_user_permissions_user_id_a95ead1b ON public.auth_user_user_permissions USING btree (user_id);


--
-- Name: auth_user_username_6821ab7c_like; Type: INDEX; Schema: public; Owner: login
--

CREATE INDEX auth_user_username_6821ab7c_like ON public.auth_user USING btree (username varchar_pattern_ops);


--
-- Name: authtoken_token_key_10f0b77e_like; Type: INDEX; Schema: public; Owner: login
--

CREATE INDEX authtoken_token_key_10f0b77e_like ON public.authtoken_token USING btree (key varchar_pattern_ops);


--
-- Name: django_admin_log_content_type_id_c4bce8eb; Type: INDEX; Schema: public; Owner: login
--

CREATE INDEX django_admin_log_content_type_id_c4bce8eb ON public.django_admin_log USING btree (content_type_id);


--
-- Name: django_admin_log_user_id_c564eba6; Type: INDEX; Schema: public; Owner: login
--

CREATE INDEX django_admin_log_user_id_c564eba6 ON public.django_admin_log USING btree (user_id);


--
-- Name: django_session_expire_date_a5c62663; Type: INDEX; Schema: public; Owner: login
--

CREATE INDEX django_session_expire_date_a5c62663 ON public.django_session USING btree (expire_date);


--
-- Name: django_session_session_key_c0390e0f_like; Type: INDEX; Schema: public; Owner: login
--

CREATE INDEX django_session_session_key_c0390e0f_like ON public.django_session USING btree (session_key varchar_pattern_ops);


--
-- Name: GlobalTag GlobalTag_status_id_7b5018a3_fk_GlobalTagStatus_id; Type: FK CONSTRAINT; Schema: public; Owner: login
--

ALTER TABLE ONLY public."GlobalTag"
    ADD CONSTRAINT "GlobalTag_status_id_7b5018a3_fk_GlobalTagStatus_id" FOREIGN KEY (status_id) REFERENCES public."GlobalTagStatus"(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: GlobalTag GlobalTag_type_id_36cf70c0_fk_GlobalTagType_id; Type: FK CONSTRAINT; Schema: public; Owner: login
--

ALTER TABLE ONLY public."GlobalTag"
    ADD CONSTRAINT "GlobalTag_type_id_36cf70c0_fk_GlobalTagType_id" FOREIGN KEY (type_id) REFERENCES public."GlobalTagType"(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: PayloadIOV PayloadIOV_payload_list_id_37321d74_fk_PayloadList_id; Type: FK CONSTRAINT; Schema: public; Owner: login
--

ALTER TABLE ONLY public."PayloadIOV"
    ADD CONSTRAINT "PayloadIOV_payload_list_id_37321d74_fk_PayloadList_id" FOREIGN KEY (payload_list_id) REFERENCES public."PayloadList"(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: PayloadList PayloadList_global_tag_id_2b35c85f_fk_GlobalTag_id; Type: FK CONSTRAINT; Schema: public; Owner: login
--

ALTER TABLE ONLY public."PayloadList"
    ADD CONSTRAINT "PayloadList_global_tag_id_2b35c85f_fk_GlobalTag_id" FOREIGN KEY (global_tag_id) REFERENCES public."GlobalTag"(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: PayloadList PayloadList_payload_type_id_7d588918_fk_PayloadType_id; Type: FK CONSTRAINT; Schema: public; Owner: login
--

ALTER TABLE ONLY public."PayloadList"
    ADD CONSTRAINT "PayloadList_payload_type_id_7d588918_fk_PayloadType_id" FOREIGN KEY (payload_type_id) REFERENCES public."PayloadType"(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_group_permissions auth_group_permissio_permission_id_84c5c92e_fk_auth_perm; Type: FK CONSTRAINT; Schema: public; Owner: login
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissio_permission_id_84c5c92e_fk_auth_perm FOREIGN KEY (permission_id) REFERENCES public.auth_permission(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_group_permissions auth_group_permissions_group_id_b120cbf9_fk_auth_group_id; Type: FK CONSTRAINT; Schema: public; Owner: login
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_group_id_b120cbf9_fk_auth_group_id FOREIGN KEY (group_id) REFERENCES public.auth_group(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_permission auth_permission_content_type_id_2f476e4b_fk_django_co; Type: FK CONSTRAINT; Schema: public; Owner: login
--

ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_content_type_id_2f476e4b_fk_django_co FOREIGN KEY (content_type_id) REFERENCES public.django_content_type(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_user_groups auth_user_groups_group_id_97559544_fk_auth_group_id; Type: FK CONSTRAINT; Schema: public; Owner: login
--

ALTER TABLE ONLY public.auth_user_groups
    ADD CONSTRAINT auth_user_groups_group_id_97559544_fk_auth_group_id FOREIGN KEY (group_id) REFERENCES public.auth_group(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_user_groups auth_user_groups_user_id_6a12ed8b_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: login
--

ALTER TABLE ONLY public.auth_user_groups
    ADD CONSTRAINT auth_user_groups_user_id_6a12ed8b_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_user_user_permissions auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm; Type: FK CONSTRAINT; Schema: public; Owner: login
--

ALTER TABLE ONLY public.auth_user_user_permissions
    ADD CONSTRAINT auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm FOREIGN KEY (permission_id) REFERENCES public.auth_permission(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_user_user_permissions auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: login
--

ALTER TABLE ONLY public.auth_user_user_permissions
    ADD CONSTRAINT auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: authtoken_token authtoken_token_user_id_35299eff_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: login
--

ALTER TABLE ONLY public.authtoken_token
    ADD CONSTRAINT authtoken_token_user_id_35299eff_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: django_admin_log django_admin_log_content_type_id_c4bce8eb_fk_django_co; Type: FK CONSTRAINT; Schema: public; Owner: login
--

ALTER TABLE ONLY public.django_admin_log
    ADD CONSTRAINT django_admin_log_content_type_id_c4bce8eb_fk_django_co FOREIGN KEY (content_type_id) REFERENCES public.django_content_type(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: django_admin_log django_admin_log_user_id_c564eba6_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: login
--

ALTER TABLE ONLY public.django_admin_log
    ADD CONSTRAINT django_admin_log_user_id_c564eba6_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- PostgreSQL database dump complete
--


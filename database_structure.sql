--
-- PostgreSQL database dump
--

SET statement_timeout = 0;
SET lock_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;

--
-- Name: plpgsql; Type: EXTENSION; Schema: -; Owner: 
--

CREATE EXTENSION IF NOT EXISTS plpgsql WITH SCHEMA pg_catalog;


--
-- Name: EXTENSION plpgsql; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION plpgsql IS 'PL/pgSQL procedural language';


SET search_path = public, pg_catalog;

--
-- Name: create_company_root_folders(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION create_company_root_folders() RETURNS trigger
    LANGUAGE plpgsql
    AS $$BEGIN

-- NEW.id = create_uuid();

WITH a AS (INSERT INTO file (mime, name) VALUES ('root', '.corporate_files') RETURNING id)
  SELECT id INTO NEW.corporate_folder_file_id FROM a;

WITH a AS (INSERT INTO file (mime, name) VALUES ('root', '.journalist_files') RETURNING id)
  SELECT id INTO NEW.journalist_folder_file_id FROM a;

RETURN NEW;

END$$;


ALTER FUNCTION public.create_company_root_folders() OWNER TO postgres;

--
-- Name: create_personal_folder_for_user(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION create_personal_folder_for_user() RETURNS trigger
    LANGUAGE plpgsql
    AS $$BEGIN

-- NEW.id = create_uuid();

WITH a AS (INSERT INTO file (mime, name) VALUES ('root', '.personal_files') RETURNING id) SELECT id INTO NEW.personal_folder_file_id FROM a;

RETURN NEW;

END$$;


ALTER FUNCTION public.create_personal_folder_for_user() OWNER TO postgres;

--
-- Name: create_uuid(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION create_uuid() RETURNS character varying
    LANGUAGE plpgsql
    AS $$DECLARE
    local_time double precision := EXTRACT(EPOCH FROM localtimestamp)::double precision;
    server_id character(3) := '001';
BEGIN
   -- f47ac10b-58cc-4372-a567-0e02b2c3d479

   return lpad(to_hex(floor(local_time)::int), 8, '0') || '-' ||
             lpad(to_hex(floor((local_time - floor(local_time))*100000)::int), 4, '0') || '-' ||
             '4' || server_id || '-' ||
             overlay(
                     to_hex((floor(random() * 65535)::int | (x'8000'::int) ) &  (x'bfff'::int)  ) ||
                     lpad(to_hex(floor(random() * 65535)::bigint),4,'0') || lpad(to_hex(floor(random() * 65535)::bigint),4,'0') || lpad(to_hex(floor(random() * 65535)::bigint),4,'0')
                  placing '-' from 5 for 0);

END
$$;


ALTER FUNCTION public.create_uuid() OWNER TO postgres;

--
-- Name: has_user_in_company_role(uuid, uuid, character varying[], character varying[]); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION has_user_in_company_role(u_id uuid, c_id uuid, inc character varying[], exc character varying[]) RETURNS boolean
    LANGUAGE plpgsql
    AS $$DECLARE
ret Boolean;
roles varchar(50)[];
BEGIN
  SELECT INTO roles role_id FROM user_company_role WHERE user_company_role.user_id=i_id AND user_company_role.company_id=c_id;
  RETURN True;
END$$;


ALTER FUNCTION public.has_user_in_company_role(u_id uuid, c_id uuid, inc character varying[], exc character varying[]) OWNER TO postgres;

--
-- Name: row_cr_md(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION row_cr_md() RETURNS trigger
    LANGUAGE plpgsql
    AS $$BEGIN

NEW.cr_tm = clock_timestamp();
NEW.md_tm = NEW.cr_tm;
RETURN NEW;

END$$;


ALTER FUNCTION public.row_cr_md() OWNER TO postgres;

--
-- Name: row_cr_md_ac(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION row_cr_md_ac() RETURNS trigger
    LANGUAGE plpgsql
    AS $$BEGIN

NEW.cr_tm = localtimestamp;
NEW.md_tm = NEW.cr_tm;
NEW.ac_tm = NEW.cr_tm;
RETURN NEW;

END$$;


ALTER FUNCTION public.row_cr_md_ac() OWNER TO postgres;

--
-- Name: row_id(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION row_id() RETURNS trigger
    LANGUAGE plpgsql
    AS $$DECLARE
    local_time double precision := EXTRACT(EPOCH FROM localtimestamp)::double precision;
    server_id character(3) := '001';
BEGIN
   -- f47ac10b-58cc-4372-a567-0e02b2c3d479

   NEW.id = create_uuid();

--   lpad(to_hex(floor(local_time)::int), 8, '0') || '-' ||
--             lpad(to_hex(floor((local_time - floor(local_time))*100000)::int), 4, '0') || '-' ||
--           '4' || server_id || '-' ||
--         overlay(
--                   to_hex((floor(random() * 65535)::int | (x'8000'::int) ) &  (x'bfff'::int)  ) ||
--                 lpad(to_hex(floor(random() * 65535)::bigint),4,'0') || lpad(to_hex(floor(random() * 65535)::bigint),4,'0') || lpad(to_hex(floor(random() * 65535)::bigint),4,'0')
--                  placing '-' from 5 for 0);


   return NEW;


END$$;


ALTER FUNCTION public.row_id() OWNER TO postgres;

--
-- Name: row_md(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION row_md() RETURNS trigger
    LANGUAGE plpgsql
    AS $$BEGIN

NEW.md_tm = clock_timestamp();
RETURN NEW;

END$$;


ALTER FUNCTION public.row_md() OWNER TO postgres;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: article; Type: TABLE; Schema: public; Owner: pfuser; Tablespace: 
--

CREATE TABLE article (
    id character varying(36) NOT NULL
);


ALTER TABLE article OWNER TO pfuser;

--
-- Name: article_version; Type: TABLE; Schema: public; Owner: pfuser; Tablespace: 
--

CREATE TABLE article_version (
    id character varying(36) NOT NULL,
    author_user_id character varying(36) NOT NULL,
    company_id character varying(36),
    name character varying(200) DEFAULT ''::character varying NOT NULL,
    short text DEFAULT ''::text NOT NULL,
    long text DEFAULT ''::text NOT NULL,
    created_from_version_id character varying(36),
    article_id character varying(36) NOT NULL
);


ALTER TABLE article_version OWNER TO pfuser;

--
-- Name: company; Type: TABLE; Schema: public; Owner: pfuser; Tablespace: 
--

CREATE TABLE company (
    id character varying(36) NOT NULL,
    name character varying(100),
    logo_file character varying(36),
    portal_consist boolean,
    author_user_id character varying(36) NOT NULL,
    country character varying(100),
    region character varying(100),
    address character varying(100),
    phone character varying(20),
    phone2 character varying(20),
    email character varying(100),
    short_description character varying(666),
    journalist_folder_file_id character varying(36),
    corporate_folder_file_id character varying(36)
);


ALTER TABLE company OWNER TO pfuser;

--
-- Name: company_right; Type: TABLE; Schema: public; Owner: pfuser; Tablespace: 
--

CREATE TABLE company_right (
    id character varying(40) NOT NULL
);


ALTER TABLE company_right OWNER TO pfuser;

--
-- Name: file; Type: TABLE; Schema: public; Owner: pfuser; Tablespace: 
--

CREATE TABLE file (
    id character varying(36) NOT NULL,
    parent_id character varying(36),
    name character varying(100) NOT NULL,
    mime character varying(30) NOT NULL,
    description character varying(666) DEFAULT ''::character varying NOT NULL,
    copyright character varying(666) DEFAULT ''::character varying NOT NULL,
    company_id character varying(36),
    author_name character varying(100) DEFAULT ''::character varying NOT NULL,
    ac_count integer DEFAULT 0 NOT NULL,
    size integer DEFAULT 0 NOT NULL,
    author_user_id character varying(36),
    cr_tm timestamp without time zone NOT NULL,
    md_tm timestamp without time zone NOT NULL,
    ac_tm timestamp without time zone NOT NULL
);


ALTER TABLE file OWNER TO pfuser;

--
-- Name: file_content; Type: TABLE; Schema: public; Owner: pfuser; Tablespace: 
--

CREATE TABLE file_content (
    id character varying(36) NOT NULL,
    content bytea
);


ALTER TABLE file_content OWNER TO pfuser;

--
-- Name: tst; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE tst (
    uid uuid NOT NULL
);


ALTER TABLE tst OWNER TO postgres;

--
-- Name: user; Type: TABLE; Schema: public; Owner: pfuser; Tablespace: 
--

CREATE TABLE "user" (
    id character varying(36) NOT NULL,
    profireader_email character varying(100),
    profireader_first_name character varying(100),
    profireader_last_name character varying(100),
    profireader_name character varying(100),
    profireader_gender character varying(6),
    profireader_link text,
    profireader_phone character varying(20),
    profireader_avatar_file_id character varying(36),
    about_me character varying(666),
    location character varying(64),
    password_hash character varying(128),
    confirmed boolean,
    registered_tm timestamp without time zone,
    last_seen timestamp without time zone,
    avatar_hash character varying(32),
    email_conf_token character varying(128),
    email_conf_tm timestamp without time zone,
    pass_reset_token character varying(128),
    pass_reset_conf_tm timestamp without time zone,
    google_id character varying(50),
    google_email character varying(100),
    google_first_name character varying(100),
    google_last_name character varying(100),
    google_name character varying(100),
    google_gender character varying(6),
    google_link text,
    google_phone character varying(20),
    facebook_id character varying(50),
    facebook_email character varying(100),
    facebook_first_name character varying(100),
    facebook_last_name character varying(100),
    facebook_name character varying(100),
    facebook_gender character varying(6),
    facebook_link text,
    facebook_phone character varying(20),
    linkedin_id character varying(50),
    linkedin_email character varying(100),
    linkedin_first_name character varying(100),
    linkedin_last_name character varying(100),
    linkedin_name character varying(100),
    linkedin_gender character varying(6),
    linkedin_link text,
    linkedin_phone character varying(20),
    twitter_id character varying(50),
    twitter_email character varying(100),
    twitter_first_name character varying(100),
    twitter_last_name character varying(100),
    twitter_name character varying(100),
    twitter_gender character varying(6),
    twitter_link text,
    twitter_phone character varying(20),
    microsoft_id character varying(50),
    microsoft_email character varying(100),
    microsoft_first_name character varying(100),
    microsoft_last_name character varying(100),
    microsoft_name character varying(100),
    microsoft_gender character varying(6),
    microsoft_link text,
    microsoft_phone character varying(20),
    yahoo_id character varying(50),
    yahoo_email character varying(100),
    yahoo_first_name character varying(100),
    yahoo_last_name character varying(100),
    yahoo_name character varying(100),
    yahoo_gender character varying(6),
    yahoo_link text,
    yahoo_phone character varying(20),
    personal_folder_file_id character varying(36),
    profireader_avatar_url character varying(200) DEFAULT '/static/no_avatar.png'::character varying NOT NULL
);


ALTER TABLE "user" OWNER TO pfuser;

--
-- Name: COLUMN "user".profireader_avatar_file_id; Type: COMMENT; Schema: public; Owner: pfuser
--

COMMENT ON COLUMN "user".profireader_avatar_file_id IS 'remove me!!!';


--
-- Name: user_company; Type: TABLE; Schema: public; Owner: pfuser; Tablespace: 
--

CREATE TABLE user_company (
    id character varying(36) NOT NULL,
    user_id character varying(36) NOT NULL,
    company_id character varying(36) NOT NULL,
    status character varying(36) NOT NULL
);


ALTER TABLE user_company OWNER TO pfuser;

--
-- Name: user_company_right; Type: TABLE; Schema: public; Owner: pfuser; Tablespace: 
--

CREATE TABLE user_company_right (
    id bigint NOT NULL,
    user_company_id character(36) NOT NULL,
    company_right_id character varying(40) NOT NULL
);


ALTER TABLE user_company_right OWNER TO pfuser;

--
-- Name: user_company_right_id_seq; Type: SEQUENCE; Schema: public; Owner: pfuser
--

CREATE SEQUENCE user_company_right_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE user_company_right_id_seq OWNER TO pfuser;

--
-- Name: user_company_right_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: pfuser
--

ALTER SEQUENCE user_company_right_id_seq OWNED BY user_company_right.id;


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: pfuser
--

ALTER TABLE ONLY user_company_right ALTER COLUMN id SET DEFAULT nextval('user_company_right_id_seq'::regclass);


--
-- Name: article_bulk_pkey; Type: CONSTRAINT; Schema: public; Owner: pfuser; Tablespace: 
--

ALTER TABLE ONLY article
    ADD CONSTRAINT article_bulk_pkey PRIMARY KEY (id);


--
-- Name: article_pkey; Type: CONSTRAINT; Schema: public; Owner: pfuser; Tablespace: 
--

ALTER TABLE ONLY article_version
    ADD CONSTRAINT article_pkey PRIMARY KEY (id);


--
-- Name: company_name_key; Type: CONSTRAINT; Schema: public; Owner: pfuser; Tablespace: 
--

ALTER TABLE ONLY company
    ADD CONSTRAINT company_name_key UNIQUE (name);


--
-- Name: company_pkey; Type: CONSTRAINT; Schema: public; Owner: pfuser; Tablespace: 
--

ALTER TABLE ONLY company
    ADD CONSTRAINT company_pkey PRIMARY KEY (id);


--
-- Name: company_right_pkey; Type: CONSTRAINT; Schema: public; Owner: pfuser; Tablespace: 
--

ALTER TABLE ONLY company_right
    ADD CONSTRAINT company_right_pkey PRIMARY KEY (id);


--
-- Name: file_content_pkey; Type: CONSTRAINT; Schema: public; Owner: pfuser; Tablespace: 
--

ALTER TABLE ONLY file_content
    ADD CONSTRAINT file_content_pkey PRIMARY KEY (id);


--
-- Name: file_pkey; Type: CONSTRAINT; Schema: public; Owner: pfuser; Tablespace: 
--

ALTER TABLE ONLY file
    ADD CONSTRAINT file_pkey PRIMARY KEY (id);


--
-- Name: tst_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY tst
    ADD CONSTRAINT tst_pkey PRIMARY KEY (uid);


--
-- Name: user_company_pk_id; Type: CONSTRAINT; Schema: public; Owner: pfuser; Tablespace: 
--

ALTER TABLE ONLY user_company
    ADD CONSTRAINT user_company_pk_id PRIMARY KEY (id);


--
-- Name: user_company_right_pkey; Type: CONSTRAINT; Schema: public; Owner: pfuser; Tablespace: 
--

ALTER TABLE ONLY user_company_right
    ADD CONSTRAINT user_company_right_pkey PRIMARY KEY (id);


--
-- Name: user_facebook_email_key; Type: CONSTRAINT; Schema: public; Owner: pfuser; Tablespace: 
--

ALTER TABLE ONLY "user"
    ADD CONSTRAINT user_facebook_email_key UNIQUE (facebook_email);


--
-- Name: user_google_email_key; Type: CONSTRAINT; Schema: public; Owner: pfuser; Tablespace: 
--

ALTER TABLE ONLY "user"
    ADD CONSTRAINT user_google_email_key UNIQUE (google_email);


--
-- Name: user_linkedin_email_key; Type: CONSTRAINT; Schema: public; Owner: pfuser; Tablespace: 
--

ALTER TABLE ONLY "user"
    ADD CONSTRAINT user_linkedin_email_key UNIQUE (linkedin_email);


--
-- Name: user_microsoft_email_key; Type: CONSTRAINT; Schema: public; Owner: pfuser; Tablespace: 
--

ALTER TABLE ONLY "user"
    ADD CONSTRAINT user_microsoft_email_key UNIQUE (microsoft_email);


--
-- Name: user_pkey; Type: CONSTRAINT; Schema: public; Owner: pfuser; Tablespace: 
--

ALTER TABLE ONLY "user"
    ADD CONSTRAINT user_pkey PRIMARY KEY (id);


--
-- Name: user_profireader_email_key; Type: CONSTRAINT; Schema: public; Owner: pfuser; Tablespace: 
--

ALTER TABLE ONLY "user"
    ADD CONSTRAINT user_profireader_email_key UNIQUE (profireader_email);


--
-- Name: user_twitter_email_key; Type: CONSTRAINT; Schema: public; Owner: pfuser; Tablespace: 
--

ALTER TABLE ONLY "user"
    ADD CONSTRAINT user_twitter_email_key UNIQUE (twitter_email);


--
-- Name: user_yahoo_email_key; Type: CONSTRAINT; Schema: public; Owner: pfuser; Tablespace: 
--

ALTER TABLE ONLY "user"
    ADD CONSTRAINT user_yahoo_email_key UNIQUE (yahoo_email);


--
-- Name: cr_md_ac; Type: TRIGGER; Schema: public; Owner: pfuser
--

CREATE TRIGGER cr_md_ac BEFORE INSERT ON file FOR EACH ROW EXECUTE PROCEDURE row_cr_md_ac();


--
-- Name: create_company_folders; Type: TRIGGER; Schema: public; Owner: pfuser
--

CREATE TRIGGER create_company_folders BEFORE INSERT ON company FOR EACH ROW EXECUTE PROCEDURE create_company_root_folders();


--
-- Name: create_personal_folder; Type: TRIGGER; Schema: public; Owner: pfuser
--

CREATE TRIGGER create_personal_folder BEFORE INSERT ON "user" FOR EACH ROW EXECUTE PROCEDURE create_personal_folder_for_user();


--
-- Name: id; Type: TRIGGER; Schema: public; Owner: pfuser
--

CREATE TRIGGER id BEFORE INSERT ON company FOR EACH ROW EXECUTE PROCEDURE row_id();


--
-- Name: id; Type: TRIGGER; Schema: public; Owner: pfuser
--

CREATE TRIGGER id BEFORE INSERT ON file FOR EACH ROW EXECUTE PROCEDURE row_id();


--
-- Name: id; Type: TRIGGER; Schema: public; Owner: pfuser
--

CREATE TRIGGER id BEFORE INSERT ON "user" FOR EACH ROW EXECUTE PROCEDURE row_id();


--
-- Name: id; Type: TRIGGER; Schema: public; Owner: pfuser
--

CREATE TRIGGER id BEFORE INSERT ON user_company FOR EACH ROW EXECUTE PROCEDURE row_id();


--
-- Name: id; Type: TRIGGER; Schema: public; Owner: pfuser
--

CREATE TRIGGER id BEFORE INSERT ON article FOR EACH ROW EXECUTE PROCEDURE row_id();


--
-- Name: id; Type: TRIGGER; Schema: public; Owner: pfuser
--

CREATE TRIGGER id BEFORE INSERT ON article_version FOR EACH ROW EXECUTE PROCEDURE row_id();


--
-- Name: article_author_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: pfuser
--

ALTER TABLE ONLY article_version
    ADD CONSTRAINT article_author_user_id_fkey FOREIGN KEY (author_user_id) REFERENCES "user"(id);


--
-- Name: article_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: pfuser
--

ALTER TABLE ONLY article_version
    ADD CONSTRAINT article_company_id_fkey FOREIGN KEY (company_id) REFERENCES company(id);


--
-- Name: company_author_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: pfuser
--

ALTER TABLE ONLY company
    ADD CONSTRAINT company_author_user_id_fkey FOREIGN KEY (author_user_id) REFERENCES "user"(id);


--
-- Name: company_logo_file_fkey; Type: FK CONSTRAINT; Schema: public; Owner: pfuser
--

ALTER TABLE ONLY company
    ADD CONSTRAINT company_logo_file_fkey FOREIGN KEY (logo_file) REFERENCES file(id);


--
-- Name: file_author_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: pfuser
--

ALTER TABLE ONLY file
    ADD CONSTRAINT file_author_user_id_fkey FOREIGN KEY (author_user_id) REFERENCES "user"(id);


--
-- Name: file_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: pfuser
--

ALTER TABLE ONLY file
    ADD CONSTRAINT file_company_id_fkey FOREIGN KEY (company_id) REFERENCES company(id);


--
-- Name: file_content_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: pfuser
--

ALTER TABLE ONLY file_content
    ADD CONSTRAINT file_content_id_fkey FOREIGN KEY (id) REFERENCES file(id);


--
-- Name: file_parent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: pfuser
--

ALTER TABLE ONLY file
    ADD CONSTRAINT file_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES file(id);


--
-- Name: fk_article_article_bulk_id; Type: FK CONSTRAINT; Schema: public; Owner: pfuser
--

ALTER TABLE ONLY article_version
    ADD CONSTRAINT fk_article_article_bulk_id FOREIGN KEY (article_id) REFERENCES article(id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: fk_article_created_from_article_id; Type: FK CONSTRAINT; Schema: public; Owner: pfuser
--

ALTER TABLE ONLY article_version
    ADD CONSTRAINT fk_article_created_from_article_id FOREIGN KEY (created_from_version_id) REFERENCES article_version(id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: fk_user_company_right_company_right_id; Type: FK CONSTRAINT; Schema: public; Owner: pfuser
--

ALTER TABLE ONLY user_company_right
    ADD CONSTRAINT fk_user_company_right_company_right_id FOREIGN KEY (company_right_id) REFERENCES company_right(id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: fk_user_personal_folder; Type: FK CONSTRAINT; Schema: public; Owner: pfuser
--

ALTER TABLE ONLY "user"
    ADD CONSTRAINT fk_user_personal_folder FOREIGN KEY (personal_folder_file_id) REFERENCES file(id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: user_company_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: pfuser
--

ALTER TABLE ONLY user_company
    ADD CONSTRAINT user_company_company_id_fkey FOREIGN KEY (company_id) REFERENCES company(id);


--
-- Name: user_company_right_user_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: pfuser
--

ALTER TABLE ONLY user_company_right
    ADD CONSTRAINT user_company_right_user_company_id_fkey FOREIGN KEY (user_company_id) REFERENCES user_company(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: user_company_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: pfuser
--

ALTER TABLE ONLY user_company
    ADD CONSTRAINT user_company_user_id_fkey FOREIGN KEY (user_id) REFERENCES "user"(id);


--
-- Name: user_profireader_avatar_file_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: pfuser
--

ALTER TABLE ONLY "user"
    ADD CONSTRAINT user_profireader_avatar_file_id_fkey FOREIGN KEY (profireader_avatar_file_id) REFERENCES file(id);


--
-- Name: public; Type: ACL; Schema: -; Owner: postgres
--

REVOKE ALL ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM postgres;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO pfuser;
GRANT ALL ON SCHEMA public TO PUBLIC;


--
-- PostgreSQL database dump complete
--


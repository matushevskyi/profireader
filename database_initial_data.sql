--
-- PostgreSQL database dump
--

SET statement_timeout = 0;
SET lock_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;

SET search_path = public, pg_catalog;

--
-- Data for Name: company_right; Type: TABLE DATA; Schema: public; Owner: pfuser
--

INSERT INTO company_right VALUES ('edit');
INSERT INTO company_right VALUES ('publish');
INSERT INTO company_right VALUES ('un_publish');
INSERT INTO company_right VALUES ('upload_files');
INSERT INTO company_right VALUES ('delete_files');
INSERT INTO company_right VALUES ('add_employee');
INSERT INTO company_right VALUES ('suspend_employee');
INSERT INTO company_right VALUES ('send_publications');
INSERT INTO company_right VALUES ('manage_access_company');
INSERT INTO company_right VALUES ('manage_access_portal');
INSERT INTO company_right VALUES ('article_priority');
INSERT INTO company_right VALUES ('manage_readers');
INSERT INTO company_right VALUES ('manage_companies_partners');
INSERT INTO company_right VALUES ('manage_comments');
INSERT INTO company_right VALUES ('owner');
INSERT INTO company_right VALUES ('comment');


--
-- PostgreSQL database dump complete
--


DROP TRIGGER tr_member_company_portal_id_cr ON member_company_portal;

DROP TRIGGER id ON portal;

DROP FUNCTION create_uuid();

DROP FUNCTION show_enum_types();

ALTER TABLE member_company_portal
	DROP CONSTRAINT fk_member_company_portal_plan_id;

ALTER TABLE reader_portal
	DROP CONSTRAINT user_portal_reader_portal_id_fkey;

DROP TABLE member_company_portal_plan;

CREATE TABLE currency (
	id character varying(10) NOT NULL,
	name character varying(100),
	"position" integer DEFAULT 0 NOT NULL,
	active boolean DEFAULT true NOT NULL
);

CREATE TABLE membership_plan (
	id character varying(36) NOT NULL,
	name character varying(100) NOT NULL,
	portal_id character varying(36) NOT NULL,
	duration character varying(50) DEFAULT '666 years'::character varying NOT NULL,
	publication_count_open integer DEFAULT (-1) NOT NULL,
	publication_count_registered integer DEFAULT 14 NOT NULL,
	publication_count_payed integer DEFAULT 88 NOT NULL,
	publication_count_confidential integer DEFAULT 0,
	price numeric(20,2) DEFAULT 13 NOT NULL,
	cr_tm timestamp without time zone DEFAULT ('now'::text)::timestamp without time zone NOT NULL,
	md_tm timestamp without time zone DEFAULT ('now'::text)::timestamp without time zone NOT NULL,
	"position" integer DEFAULT 0 NOT NULL,
	status pr_membership_plan_status DEFAULT 'ACTIVE'::pr_membership_plan_status NOT NULL,
	currency_id character varying(5) DEFAULT 'UAH'::character varying NOT NULL,
	auto_apply boolean DEFAULT false NOT NULL
);

COMMENT ON TABLE membership_plan IS 'persistent';

CREATE TABLE membership_plan_issued (
	id character varying(36) NOT NULL,
	cr_tm timestamp without time zone NOT NULL,
	md_tm timestamp without time zone NOT NULL,
	stopped_tm timestamp without time zone,
	price numeric(20,2) NOT NULL,
	duration character varying(50) NOT NULL,
	publication_count_open integer NOT NULL,
	publication_count_registered integer NOT NULL,
	publication_count_payed integer NOT NULL,
	publication_count_confidential integer DEFAULT 0,
	started_by_user_id character varying(36),
	stopped_by_user_id character varying(36),
	membership_plan_id character varying(36) NOT NULL,
	member_company_portal_id character varying(36) NOT NULL,
	started_tm timestamp without time zone,
	name character varying(100) NOT NULL,
	currency_id character varying(5) DEFAULT 'UAH'::character varying NOT NULL,
	portal_id character varying(36) NOT NULL,
	company_id character varying(36) NOT NULL,
	requested_by_user_id character varying(36) NOT NULL,
	auto_renew boolean DEFAULT true NOT NULL,
	calculated_stopping_tm timestamp without time zone,
	auto_apply boolean DEFAULT false NOT NULL,
	confirmed boolean DEFAULT false NOT NULL
);

ALTER TABLE member_company_portal
	DROP COLUMN member_company_portal_plan_id,
	ADD COLUMN current_membership_plan_issued_id character varying(36) NOT NULL,
	ADD COLUMN requested_membership_plan_issued_id character varying(36),
	ADD COLUMN md_tm timestamp without time zone NOT NULL,
	ADD COLUMN request_membership_plan_issued_immediately boolean DEFAULT false NOT NULL;

ALTER TABLE portal
	ADD COLUMN default_membership_plan_id character varying(36) NOT NULL,
	ADD COLUMN cr_tm timestamp without time zone NOT NULL,
	ADD COLUMN md_tm timestamp without time zone NOT NULL;

ALTER TABLE "translate"
	ADD COLUMN comment text DEFAULT ''::text NOT NULL;

CREATE OR REPLACE FUNCTION __change_enum_type(enum_name character varying, enum_values character varying[]) RETURNS integer
    LANGUAGE plpgsql
    AS $$DECLARE

tcs record;
cnt integer;

BEGIN

CREATE TEMP TABLE cnts AS SELECT table_name as tab, column_name as col, column_default as cd FROM information_schema.columns WHERE data_type = 'USER-DEFINED' AND udt_name = enum_name;

cnt = 0;
FOR tcs IN SELECT * FROM cnts LOOP
  EXECUTE 'ALTER TABLE "' || tcs.tab || '" ALTER COLUMN "' || tcs.col || '" TYPE character varying(1000)';
  EXECUTE 'ALTER TABLE "' || tcs.tab || '" ALTER "' || tcs.col || '" DROP DEFAULT';
  cnt = cnt +1;
END LOOP;


EXECUTE 'DROP TYPE "' || enum_name || '"';
EXECUTE 'CREATE TYPE ' || enum_name || ' AS ENUM (''' || array_to_string(enum_values, ''', ''') || ''')';

FOR tcs IN SELECT * FROM cnts LOOP
  EXECUTE 'ALTER TABLE "' || tcs.tab || '" ALTER COLUMN "' || tcs.col || '" TYPE "' || enum_name || '" USING "'|| tcs.col || '"::"' || enum_name || '"';
  IF tcs.cd IS NULL THEN
    EXECUTE 'ALTER TABLE "' || tcs.tab || '" ALTER COLUMN "' || tcs.col || '" SET DEFAULT(NULL)';
  ELSE
    EXECUTE 'ALTER TABLE "' || tcs.tab || '" ALTER COLUMN "' || tcs.col || '" SET DEFAULT(' || tcs.cd || ')';
  END IF;
END LOOP;

RETURN cnt;

END$$;

CREATE OR REPLACE FUNCTION __has_rights(check_in bigint, right_bits integer[]) RETURNS boolean
    LANGUAGE plpgsql
    AS $$DECLARE

expon smallint;
binary_rights bigint;

BEGIN

binary_rights = 0;

FOREACH expon IN ARRAY right_bits LOOP
  IF expon<0  OR expon>127 THEN
    RAISE EXCEPTION 'right bits have to be >=0 and <=127 --> % given', expon;
  ELSE
    binary_rights = binary_rights | (1 << expon);
  END IF;
END LOOP;

RETURN (check_in & binary_rights)!=0;

END$$;

CREATE OR REPLACE FUNCTION __has_rights(check_in bigint, right_bit integer) RETURNS boolean
    LANGUAGE plpgsql
    AS $$BEGIN

RETURN __has_rights(check_in, ARRAY[right_bit]);

END$$;

CREATE OR REPLACE FUNCTION __show_enum_types() RETURNS TABLE(schema_name character varying, type_name character varying, type_values character varying)
    LANGUAGE plpgsql
    AS $$
BEGIN

return query select n.nspname::character varying as schema_name, t.typname::character varying as type_name, string_agg(e.enumlabel, ', ')::character varying FROM pg_type t JOIN pg_enum e ON t.oid = e.enumtypid JOIN pg_catalog.pg_namespace n ON n.oid = t.typnamespace GROUP BY schema_name, type_name;

END
$$;

CREATE OR REPLACE FUNCTION __show_enum_types(enum_schema character varying) RETURNS SETOF record
    LANGUAGE plpgsql
    AS $$BEGIN

return query select n.nspname::character varying, t.typname::character varying, string_agg(e.enumlabel, '', '')::character varying FROM pg_type t JOIN pg_enum e ON t.oid = e.enumtypid JOIN pg_catalog.pg_namespace n ON n.oid = t.typnamespace GROUP BY e_schema, enum_name;

END$$;

CREATE OR REPLACE FUNCTION aa_membership_hold_unhold_publications(membership_id character varying, visibility pr_enum_publication_visibility, current_membership_plan_issued_id character varying, default_membership_plan_id character varying) RETURNS integer
    LANGUAGE plpgsql
    AS $$DECLARE
  issued_plan_id character varying;
  lim integer;
  port_id integer;
  comp_id integer;
  cnt_hold integer;
  cnt_pub integer;
BEGIN

  SELECT portal_id, company_id, current_membership_plan_issued_id INTO port_id, comp_id, issued_plan_id  FROM member_company_portal WHERE member_company_portal.id = membership_id;

  EXECUTE 'SELECT INTO lim publication_count_' || lower(visibility) || ' FROM membership_plan_issued WHERE membership_plan_issued.id = ''' || issued_plan_id || '''';

  SELECT INTO cnt_pub COUNT(*) FROM publication
        LEFT JOIN portal_division ON portal_division.id = publication.portal_division_id
        WHERE publication.visibility = vis AND publication.status = 'PUBLISHED' AND portal_division.portal_id = port_id;

  SELECT INTO cnt_hold COUNT(*) FROM publication
        LEFT JOIN portal_division ON portal_division.id = publication.portal_division_id
        WHERE publication.visibility = vis AND publication.status = 'HOLDED' AND portal_division.portal_id = port_id;

  IF lim>0 AND cnt_pub>lim THEN

    UPDATE publication SET publication.status = 'HOLDED' WHERE id IN
          (SELECT id FROM publication as ps LEFT JOIN portal_division ON portal_division.id = ps.portal_division_id
           WHERE ps.visibility = vis AND ps.status = 'PUBLISHED' AND portal_division.portal_id = port_id
           ORDER BY ps.publishing_tm ASC
           LIMIT cnt_pub - lim);

  END IF;

  IF lim>0 AND cnt_pub<lim AND cnt_hold>0 THEN

    UPDATE publication SET publication.status = 'PUBLISHED' WHERE id IN
          (SELECT id FROM publication as ps LEFT JOIN portal_division ON portal_division.id = ps.portal_division_id
           WHERE ps.visibility = vis AND ps.status = 'HOLDED' AND portal_division.portal_id = port_id
           ORDER BY ps.publishing_tm DESC
           LIMIT lim - cnt_pub);

  END IF;


  IF lim<=0 AND cnt_hold>0 THEN

    UPDATE publication SET publication.status = 'PUBLISHED' WHERE id IN
          (SELECT id FROM publication as ps LEFT JOIN portal_division ON portal_division.id = ps.portal_division_id
           WHERE ps.visibility = vis AND ps.status = 'HOLDED' AND portal_division.portal_id = port_id);
  END IF;

  RETURN 0;

END$$;

CREATE OR REPLACE FUNCTION create_uuid(existing_id character varying) RETURNS character varying
    LANGUAGE plpgsql
    AS $$DECLARE
BEGIN
   -- f47ac10b-58cc-4372-a567-0e02b2c3d479

   return (case when existing_id IS NULL then create_uuid_from_timestamp_and_server_id(localtimestamp, '001') else existing_id end);
END$$;

CREATE OR REPLACE FUNCTION membership_hold_unhold_publications(membership_id character varying, a_visibility pr_enum_publication_visibility) RETURNS integer
    LANGUAGE plpgsql
    AS $$DECLARE
  issued_plan_id character varying;
  lim integer;
  port_id character varying;
  comp_id character varying;
  cnt_hold integer;
  cnt_pub integer;
  ret integer;
BEGIN

  SELECT portal_id, company_id, current_membership_plan_issued_id INTO port_id, comp_id, issued_plan_id FROM member_company_portal WHERE member_company_portal.id = membership_id;

  EXECUTE 'SELECT publication_count_' || lower(a_visibility::character varying) || ' FROM membership_plan_issued WHERE membership_plan_issued.id = ''' || issued_plan_id || '''' INTO lim;

  SELECT INTO cnt_pub COUNT(*) FROM publication
        LEFT JOIN portal_division ON portal_division.id = publication.portal_division_id
        WHERE publication.visibility = a_visibility AND publication.status = 'PUBLISHED' AND portal_division.portal_id = port_id;

  SELECT INTO cnt_hold COUNT(*) FROM publication
        LEFT JOIN portal_division ON portal_division.id = publication.portal_division_id
        WHERE publication.visibility = a_visibility AND publication.status = 'HOLDED' AND portal_division.portal_id = port_id;

  IF lim>=0 AND cnt_pub>lim THEN

      WITH updated_rows AS (UPDATE publication SET status = 'HOLDED' WHERE publication.id IN
          (SELECT ps.id FROM publication as ps LEFT JOIN portal_division ON portal_division.id = ps.portal_division_id
           WHERE ps.visibility = a_visibility AND ps.status = 'PUBLISHED' AND portal_division.portal_id = port_id
           ORDER BY ps.publishing_tm ASC
           LIMIT cnt_pub - lim) RETURNING 1) SELECT count(*) INTO ret;

    RETURN -ret;

  END IF;

  IF lim>=0 AND cnt_pub<lim AND cnt_hold>0 THEN

    WITH updated_rows AS (UPDATE publication SET status = 'PUBLISHED' WHERE id IN
          (SELECT ps.id FROM publication as ps LEFT JOIN portal_division ON portal_division.id = ps.portal_division_id
           WHERE ps.visibility = a_visibility AND ps.status = 'HOLDED' AND portal_division.portal_id = port_id
           ORDER BY ps.publishing_tm DESC
           LIMIT lim - cnt_pub) RETURNING 1) SELECT count(*) INTO ret;

    RETURN ret;

  END IF;


  IF lim<0 AND cnt_hold>0 THEN

    WITH updated_rows AS (UPDATE publication SET status = 'PUBLISHED' WHERE id IN
          (SELECT ps.id FROM publication as ps LEFT JOIN portal_division ON portal_division.id = ps.portal_division_id
           WHERE ps.visibility = a_visibility AND ps.status = 'HOLDED' AND portal_division.portal_id = port_id) RETURNING 1) SELECT count(*) INTO ret;

    RETURN ret;

  END IF;

  RETURN 0;

END$$;

CREATE OR REPLACE FUNCTION row_id() RETURNS trigger
    LANGUAGE plpgsql
    AS $$DECLARE
    local_time double precision := EXTRACT(EPOCH FROM localtimestamp)::double precision;
    server_id character(3) := '001';
BEGIN
   -- f47ac10b-58cc-4372-a567-0e02b2c3d479

   NEW.id = create_uuid(NEW.id);

--   lpad(to_hex(floor(local_time)::int), 8, '0') || '-' ||
--             lpad(to_hex(floor((local_time - floor(local_time))*100000)::int), 4, '0') || '-' ||
--           '4' || server_id || '-' ||
--         overlay(
--                   to_hex((floor(random() * 65535)::int | (x'8000'::int) ) &  (x'bfff'::int)  ) ||
--                 lpad(to_hex(floor(random() * 65535)::bigint),4,'0') || lpad(to_hex(floor(random() * 65535)::bigint),4,'0') || lpad(to_hex(floor(random() * 65535)::bigint),4,'0')
--                  placing '-' from 5 for 0);


   return NEW;


END$$;

CREATE OR REPLACE FUNCTION row_id_cr() RETURNS trigger
    LANGUAGE plpgsql
    AS $$BEGIN
   NEW.id = create_uuid(NEW.id);

   NEW.cr_tm = clock_timestamp();

   return NEW;

END$$;

CREATE OR REPLACE FUNCTION row_id_cr_md() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
   NEW.id = create_uuid(NEW.id);

   NEW.cr_tm = clock_timestamp();
   NEW.md_tm = NEW.cr_tm;

   return NEW;

END$$;

CREATE OR REPLACE FUNCTION row_id_cr_md_ac() RETURNS trigger
    LANGUAGE plpgsql
    AS $$BEGIN
NEW.id = create_uuid(NEW.id);
NEW.cr_tm = clock_timestamp();
NEW.md_tm = NEW.cr_tm;
NEW.ac_tm = NEW.cr_tm;
RETURN NEW;

END$$;

ALTER TABLE currency
	ADD CONSTRAINT currency_pkey PRIMARY KEY (id);

ALTER TABLE membership_plan
	ADD CONSTRAINT portal_plan_pkey PRIMARY KEY (id);

ALTER TABLE membership_plan_issued
	ADD CONSTRAINT membership_plan_usage_pkey PRIMARY KEY (id);

ALTER TABLE member_company_portal
	ADD CONSTRAINT uk_membership_id_company_portal UNIQUE (id, company_id, portal_id);

ALTER TABLE member_company_portal
	ADD CONSTRAINT fk_mcp_current_membership_plan_issued FOREIGN KEY (current_membership_plan_issued_id) REFERENCES membership_plan_issued(id) ON UPDATE RESTRICT ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE member_company_portal
	ADD CONSTRAINT fk_mcp_requested_membership_plan_issued FOREIGN KEY (requested_membership_plan_issued_id) REFERENCES membership_plan_issued(id) ON UPDATE RESTRICT ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE membership_plan
	ADD CONSTRAINT uk_for_membership_plan_issued_fk UNIQUE (id, portal_id);

ALTER TABLE membership_plan
	ADD CONSTRAINT fk_membership_plan_portal_id FOREIGN KEY (portal_id) REFERENCES portal(id) ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE membership_plan_issued
	ADD CONSTRAINT fk_membership_plan_issued_membership_company_portal FOREIGN KEY (member_company_portal_id, company_id, portal_id) REFERENCES member_company_portal(id, company_id, portal_id) ON UPDATE CASCADE ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE membership_plan_issued
	ADD CONSTRAINT fk_membership_plan_issued_membership_plan FOREIGN KEY (membership_plan_id, portal_id) REFERENCES membership_plan(id, portal_id) ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE portal
	ADD CONSTRAINT portal_default_membership_plan FOREIGN KEY (default_membership_plan_id) REFERENCES membership_plan(id) ON UPDATE RESTRICT ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE reader_portal
	ADD CONSTRAINT fk_reader_portal_portal_id FOREIGN KEY (portal_id) REFERENCES portal(id) ON UPDATE CASCADE ON DELETE CASCADE;

CREATE TRIGGER tr_member_company_portal_insert
	BEFORE INSERT ON member_company_portal
	FOR EACH ROW
	EXECUTE PROCEDURE row_id_cr_md();

CREATE TRIGGER tr_member_company_portal_updae
	BEFORE UPDATE ON member_company_portal
	FOR EACH ROW
	EXECUTE PROCEDURE row_md();

CREATE TRIGGER tr_membership_plan_id_cr_md
	BEFORE INSERT ON membership_plan
	FOR EACH ROW
	EXECUTE PROCEDURE row_id_cr_md();

CREATE TRIGGER tr_membership_plan_usage
	BEFORE INSERT ON membership_plan_issued
	FOR EACH ROW
	EXECUTE PROCEDURE row_id_cr_md();

CREATE TRIGGER tr_plan_id_tm
	BEFORE INSERT ON portal
	FOR EACH ROW
	EXECUTE PROCEDURE row_id_cr_md();

CREATE TRIGGER tr_plan_md_tm
	BEFORE UPDATE ON portal
	FOR EACH ROW
	EXECUTE PROCEDURE row_md();

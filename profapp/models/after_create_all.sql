

CREATE OR REPLACE FUNCTION has_user_in_company_role(u_id uuid, c_id uuid, inc character varying[], exc character varying[]) RETURNS boolean
    LANGUAGE plpgsql
    AS $$DECLARE
ret Boolean;
roles varchar(50)[];
BEGIN
  SELECT INTO roles role_id FROM user_company_role WHERE user_company_role.user_id=i_id AND user_company_role.company_id=c_id;
  RETURN True;
END$$;

CREATE OR REPLACE FUNCTION row_cr_md() RETURNS trigger
    LANGUAGE plpgsql
    AS $$BEGIN

NEW.cr_tm = clock_timestamp();
NEW.md_tm = NEW.cr_tm;
RETURN NEW;

END$$;

CREATE OR REPLACE FUNCTION row_cr_md_ac() RETURNS trigger
    LANGUAGE plpgsql
    AS $$BEGIN

NEW.cr_tm = localtimestamp;
NEW.md_tm = NEW.cr_tm;
NEW.ac_tm = NEW.cr_tm;
RETURN NEW;

END$$;

CREATE OR REPLACE FUNCTION row_id() RETURNS trigger
    LANGUAGE plpgsql
    AS $$DECLARE
    local_time double precision := EXTRACT(EPOCH FROM localtimestamp)::double precision;
    server_id character(3) := '001';
BEGIN
   -- f47ac10b-58cc-4372-a567-0e02b2c3d479

   NEW.id = lpad(to_hex(floor(local_time)::int), 8, '0') || '-' ||
             lpad(to_hex(floor((local_time - floor(local_time))*100000)::int), 4, '0') || '-' ||
             '4' || server_id || '-' ||
             overlay(
                     to_hex((floor(random() * 65535)::int | (x'8000'::int) ) &  (x'bfff'::int)  ) ||
                     lpad(to_hex(floor(random() * 65535)::bigint),4,'0') || lpad(to_hex(floor(random() * 65535)::bigint),4,'0') || lpad(to_hex(floor(random() * 65535)::bigint),4,'0')
                  placing '-' from 5 for 0);


   return NEW;


END$$;

CREATE OR REPLACE FUNCTION row_md() RETURNS trigger
    LANGUAGE plpgsql
    AS $$BEGIN

NEW.md_tm = clock_timestamp();
RETURN NEW;

END$$;

CREATE TRIGGER id BEFORE INSERT ON user_company_role FOR EACH ROW EXECUTE PROCEDURE row_id();


CREATE TRIGGER id
	BEFORE INSERT ON company
	FOR EACH ROW
	EXECUTE PROCEDURE row_id();

CREATE TRIGGER cr_md_ac
	BEFORE INSERT ON file
	FOR EACH ROW
	EXECUTE PROCEDURE row_cr_md_ac();

CREATE TRIGGER id
	BEFORE INSERT ON file
	FOR EACH ROW
	EXECUTE PROCEDURE row_id();

CREATE TRIGGER id
	BEFORE INSERT ON "user"
	FOR EACH ROW
	EXECUTE PROCEDURE row_id();


INSERT INTO company_right VALUES ('comment');
INSERT INTO company_right VALUES ('publish');
INSERT INTO company_right VALUES ('unpublish');
INSERT INTO company_right VALUES ('write_articles');
INSERT INTO company_right VALUES ('moderate_comments');
INSERT INTO company_right VALUES ('manage_content');
INSERT INTO company_right VALUES ('manage_members');
INSERT INTO company_right VALUES ('manage_access');
INSERT INTO company_right VALUES ('transfer_ownership');

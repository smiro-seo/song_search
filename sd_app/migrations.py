from .constants import DB_NAME, default_improver_prompt, default_model
from sqlalchemy.sql import text
from sqlalchemy import create_engine

engine = create_engine(f"sqlite:///instance/{DB_NAME}")

query_100= [text("SELECT 'first version'")]
query_101= [text("ALTER TABLE search ADD COLUMN improver_prompt STRING;"),
    text("ALTER TABLE user ADD COLUMN default_improver_prompt STRING;"),
    text(f"UPDATE user SET default_improver_prompt='{default_improver_prompt}';")]
query_102= [text("ALTER TABLE search ADD COLUMN improved BOOLEAN;"),
    text(f"UPDATE search SET improved=FALSE;")]
query_1022= [text("ALTER TABLE search ADD COLUMN model STRING;"),
    text(f"UPDATE search SET model='{default_model}';")]

queries = {'1.0.0':query_100, '1.0.1':query_101, '1.0.2.1':query_102, '1.0.2.2':query_1022}
version_list = list(queries.keys())

def check_db_version():
    with engine.connect() as con:
        print("Checking DB version...")
        db_version = find_db_version(con)
        print("Database version: "  + db_version)

        if db_version != version_list[-1]:
            index = version_list.index(db_version)
            for v in version_list[index+1:]:
                print("Running migration for version " + v)
                for q in queries[v]: con.execute(q)
            
        elif db_version not in version_list:
            for v in version_list:
                con.execute(queries[v])
        
        else: return print("Database up to date")

        print("Migrations finished. Current version: " + version_list[-1])
        set_db_version(con, version_list[-1])


    return 



def find_db_version(con):
    db_version = con.execute("SELECT name, value FROM parameters WHERE name='db_version'").mappings().all()

    if len(db_version) == 0:
        con.execute(f"INSERT INTO parameters VALUES ('db_version', '{version_list[0]}')")
        return version_list[0]
    else:
        return db_version[0]['value']


def set_db_version(con, version):
    db_version = con.execute("SELECT name, value FROM parameters WHERE name='db_version'").mappings().all()
    if len(db_version) == 0:
        con.execute(f"INSERT INTO parameters VALUES ('db_version', '{version}')")
        return version_list[0]
    else:
       con.execute(f"UPDATE parameters SET value='{version}' WHERE name='db_version'")

def set_db_version_current():
    with engine.connect() as con:
        set_db_version(con, version_list[-1])
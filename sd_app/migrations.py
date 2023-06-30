from .constants import DB_NAME, default_improver_prompt, default_model
from sqlalchemy.sql import text
from sqlalchemy import create_engine

engine = create_engine(f"sqlite:///instance/{DB_NAME}")
default_img_prompt = 'Based on the following article summary, provide a suitable prompt for a text-to-image generative model. Focus on the concept of [keyword]. Below are some examples:\
 Example 1:\
 A dreamy, vibrant illustration about [keyword]; aesthetically pleasing anime style, trending on popular art platforms, minutely detailed, with precise, sharp lines, a composition that qualifies as an award-winning illustration, presented in 4K resolution, inspired by master artists like Eugene de Blaas and Ross Tran, employing a vibrant color palette, intricately detailed.\
 Example 2:\
 An illustration exuding van gogh distinctive style; an ultra-detailed and hyper-realistic portrayal of [keyword], designed with Lisa Frank aesthetics, featuring popular art elements such as butterflies and florals, sharp focus, akin to a high-quality studio photograph, with meticulous detailing.'

query_100= [text("SELECT 'first version'")]
query_101= [text("ALTER TABLE search ADD COLUMN improver_prompt STRING;"),
    text("ALTER TABLE user ADD COLUMN default_improver_prompt STRING;"),
    text(f"UPDATE user SET default_improver_prompt='{default_improver_prompt}';")]
query_102= [text("ALTER TABLE search ADD COLUMN improved BOOLEAN;"),
    text(f"UPDATE search SET improved=FALSE;")]
query_1022= [text("ALTER TABLE search ADD COLUMN model STRING;"),
    text(f"UPDATE search SET model='{default_model}';")]
query_103= [
    text("ALTER TABLE search ADD COLUMN improved_song BOOLEAN;"),
    text("ALTER TABLE search ADD COLUMN improved_intro BOOLEAN;"),
    text("ALTER TABLE search DROP COLUMN improved;"),
    text(f"UPDATE search SET improved_song=FALSE;"),
    text(f"UPDATE search SET improved_intro=FALSE;"),
    text("ALTER TABLE search ADD COLUMN model STRING;"),
    text(f"UPDATE search SET model='{default_model}';")
]
query_1031=[
    "UPDATE user SET default_intro_prompt='placeholder' WHERE default_intro_prompt is NULL;",
    "UPDATE user SET default_prompt='placeholder' WHERE default_prompt is NULL;",
    "UPDATE user SET default_improver_prompt='placeholder' WHERE default_improver_prompt is NULL;",
    "UPDATE user SET default_intro_prompt_artist='placeholder' WHERE default_intro_prompt_artist is NULL;",
    "UPDATE user SET default_prompt_artist='placeholder' WHERE default_prompt_artist is NULL;"
    ]

query_104=[
    'ALTER TABLE search ADD COLUMN "by" STRING;',
    'UPDATE search SET "by"=\'artist\' WHERE by_artist=1;',
    'UPDATE search SET "by"=\'keyword\' WHERE by_artist=0;',
    "ALTER TABLE search DROP COLUMN by_artist"
]
query_105=[
    'ALTER TABLE search ADD COLUMN image_prompt_keywords_str STRING;',
    'ALTER TABLE search ADD COLUMN image_nprompt_keywords_str STRING;'
]
query_106=[
    'ALTER TABLE user ADD COLUMN default_img_prompt STRING;',
    'ALTER TABLE search ADD COLUMN img_prompt STRING;',
    f"UPDATE user SET default_img_prompt = '{default_img_prompt}' ;"
]

queries = {
    '1.0.0':query_100,
    '1.0.1':query_101,
    '1.0.2':query_102,
    '1.0.2.2':query_1022,
    '1.0.2.3':query_100,
    '1.0.3':query_103,
    '1.0.3.1':query_1031,
    '1.0.4':query_104,
    '1.0.5':query_105,
    '1.0.6':query_106
}


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
                for q in queries[v]: 
                    try:
                        con.execute(q)
                    except:
                        print("Error while migrating")
            
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
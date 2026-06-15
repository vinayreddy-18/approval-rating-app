from app import create_app
from app.database import init_db, seed_politicians

init_db()
seed_politicians()

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
